from collections import deque
from typing import (
    Any,
    Callable,
    Deque,
    Iterable,
    List,
    MutableSequence,
    Optional,
    Sequence,
    Set,
    Type,
    Union,
)

from bs4 import BeautifulSoup
from bs4.builder._lxml import LXMLTreeBuilder
from bs4.element import NavigableString, Tag
from lxml.etree import HTMLParser
from pydantic import ValidationError

from ..nodes import AnyNode, InvalidNode, Node, NodeType, TextNode
from .mapper import NodeTypesMapper

ParsedNode = Union[Node, InvalidNode, None]


class MarkupParserError(ValueError):
    reason: ValidationError
    context: str

    def __init__(self, reason: ValidationError, context: str = ''):
        self.reason = reason
        self.context = context


class MarkupParser:
    builder: 'TreeBuilder'
    soup: BeautifulSoup
    nodestack: Deque[Node]
    nodes: Iterable[AnyNode] = ()
    errors: Sequence[MarkupParserError] = ()

    def __init__(
        self,
        markup: str,
        mapper: NodeTypesMapper = None,
        postprocessors: Iterable[Callable] = None,
        context: dict = None,
        include: Set[str] = None,
        exclude: Set[str] = None,
        raise_validation_error: bool = False,
        builder_cls: Type['TreeBuilder'] = None,
        nodetasks: MutableSequence = None,
    ):
        self.nodestack = deque()
        self.builder = (builder_cls or TreeBuilder)(
            mapper=mapper,
            context=context,
            include=include,
            exclude=exclude,
            raise_validation_error=raise_validation_error,
            nodetasks=nodetasks,
            nodestack=self.nodestack,
        )
        self.soup = BeautifulSoup(
            markup=markup, builder=self.builder, element_classes=_ELEMENT_CLASSES,
        )
        body: TagNode = self.soup.body
        if not body:
            return

        # To map relation rules between elements, we need to have the whole soup built
        for relation, node_type in mapper.relations_rules if mapper else ():
            for tag in relation.select(body):
                self.builder.recreate_tag_node(tag, node_type)

        self.nodes = body.node.children if isinstance(body.node, Node) else ()
        self.errors = self.builder.errors

        # Apply postprocessors
        if postprocessors:
            for node in self.nodestack:
                for postprocess in postprocessors:
                    postprocess(node)


class TreeBuilder(LXMLTreeBuilder):
    mapper: NodeTypesMapper
    context: dict
    disallowed_nodes: Set[str]
    allowed_nodes: Set[str]
    errors: List[MarkupParserError]
    raise_validation_error: bool
    nodetasks: Optional[MutableSequence]
    nodestack: MutableSequence

    def __init__(
        self,
        *args: Any,
        mapper: NodeTypesMapper = None,
        context: dict = None,
        exclude: Set[str] = None,
        include: Set[str] = None,
        raise_validation_error: bool = False,
        nodetasks: MutableSequence = None,
        nodestack: MutableSequence = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.mapper = mapper or NodeTypesMapper()
        self.context = context or {}
        self.disallowed_nodes = exclude or set()
        if include:
            self.allowed_nodes = include - self.disallowed_nodes | {'html', 'body'}
        else:
            self.allowed_nodes = set()
        self.raise_validation_error = raise_validation_error
        self.errors = []
        self.nodetasks = nodetasks
        self.nodestack = nodestack if nodestack is not None else deque()

    def parser_for(self, *args: Any, **kwargs: Any) -> HTMLParser:
        return HTMLParser(target=self, strip_cdata=False, recover=True, remove_comments=True)

    def create_node_from_tag(self, tag: 'TagNode', node_type: NodeType = None) -> ParsedNode:
        # Use tag name as node kind value by default,
        # find declared schema class, skip processing if node kind disallowed
        node_kind = tag.name
        node_type = node_type or self.mapper.find_tag_node_type(tag)
        if node_type != self.mapper.default_node_type:
            node_kind = node_type.get_node_kind_value()
        if (
            node_kind in self.disallowed_nodes
            or self.allowed_nodes
            and node_kind not in self.allowed_nodes
        ):
            return None

        # Get & transform tag attributes
        node_attrs = node_type.prepare_attrs(tag.attrs)

        # Create node from class, collect/raise error
        try:
            node = node_type(kind=node_kind, **node_attrs)
        except ValidationError as exc:
            if self.raise_validation_error:
                raise exc
            self.errors.append(MarkupParserError(reason=exc, context=str(tag)))
            return InvalidNode(tagname=node_kind, **node_attrs)

        # Pass outer context
        parent_node = tag.parent_node if isinstance(tag.parent_node, Node) else None
        node.update_context(parent=parent_node, **self.context)

        # node.children must be set as instance attribute, otherwise Pydantic uses iterators
        node.children = deque()

        # Add node post-init task to queue
        self.node_post_init(node)

        # Add node to stack for further postprocessing
        self.nodestack.append(node)

        return node

    def recreate_tag_node(self, tag: 'TagNode', updated_node_type: NodeType) -> None:
        updated_node = self.create_node_from_tag(tag, updated_node_type)
        if not isinstance(updated_node, Node):
            return

        # No currently set node -> no update needed
        if not tag.node:
            tag.node = updated_node
            return

        updated_node.children = tag.node.children  # type: ignore
        current_node_id = id(tag.node)
        tag.node = updated_node
        # Top-level tag -> no references update
        if not tag.parent:
            return

        for i, sibling in enumerate(tag.parent.node.children):
            if id(sibling) == current_node_id:
                tag.parent.node.children[i] = tag.node
                break

    def node_post_init(self, node: Node) -> None:
        if self.nodetasks is None:
            return
        task = node.post_init_method
        if task:
            self.nodetasks.append(task)


class TagContents(deque):
    ref: ParsedNode

    def __init__(self, ref: ParsedNode):
        super().__init__()
        self.ref = ref

    def append(self, el: Union['TagNode', 'StringNode']) -> None:
        if el.node and isinstance(self.ref, Node):
            self.ref.children.append(el.node)
        super().append(el)


class TagNode(Tag):
    node: ParsedNode = None
    contents: TagContents

    def __init__(
        self, parser: HTMLParser = None, builder: TreeBuilder = None, *args: Any, **kwargs: Any,
    ):
        builder = builder or TreeBuilder()
        super().__init__(parser, builder, *args, **kwargs)
        node = builder.create_node_from_tag(self)
        if node:
            self.node = node
            self.contents = TagContents(ref=self.node)

    @property
    def parent_node(self) -> ParsedNode:
        parent_tag: TagNode = self.parent
        return parent_tag.node if parent_tag and parent_tag.name != 'body' else None


class StringNode(NavigableString):
    node: Optional[TextNode]

    def __new__(cls, value: str):  # type: ignore
        string = super().__new__(cls, value)
        string.node = TextNode.create(value) if value != '\n' else None
        return string


_ELEMENT_CLASSES = {Tag: TagNode, NavigableString: StringNode}
