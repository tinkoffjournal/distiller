from collections import deque
from typing import Any, Iterable, List, MutableSequence, Optional, Sequence, Set, Tuple, Union

from bs4 import BeautifulSoup
from bs4.builder._lxml import LXMLTreeBuilder
from bs4.element import NavigableString, Tag
from lxml.etree import HTMLParser
from pydantic import ValidationError

from distiller.nodes import AnyNode, Node, NodeType, TextNode, invalid_node

from .mapper import NodeTypesMapper


class MarkupParserError(ValueError):
    reason: ValidationError
    context: str

    def __init__(self, reason: ValidationError, context: str = ''):
        self.reason = reason
        self.context = context


def parse_markup(
    markup: str,
    mapper: NodeTypesMapper = None,
    context: dict = None,
    include: Set[str] = None,
    exclude: Set[str] = None,
    raise_validation_error: bool = False,
    queue: MutableSequence = None,
) -> Tuple[Iterable[AnyNode], Sequence[MarkupParserError]]:
    builder = TreeBuilder(
        mapper=mapper,
        context=context,
        include=include,
        exclude=exclude,
        raise_validation_error=raise_validation_error,
        queue=queue,
    )
    body: TagNode = BeautifulSoup(
        markup=markup, builder=builder, element_classes=_ELEMENT_CLASSES,
    ).body
    if not body:
        return (), ()

    # To map relation rules between elements, we need to have the whole soup built
    for relation, node_type in mapper.relations_rules if mapper else ():
        for tag in relation.select(body):
            builder.recreate_tag_node(tag, node_type)

    nodes = body.node.children if body.node else ()
    return nodes, builder.errors


class TreeBuilder(LXMLTreeBuilder):
    mapper: NodeTypesMapper
    context: dict
    include: Set[str]
    exclude: Set[str]
    errors: List[MarkupParserError]
    raise_validation_error: bool
    queue: Optional[MutableSequence]

    def __init__(
        self,
        *args: Any,
        mapper: NodeTypesMapper = None,
        context: dict = None,
        include: Set[str] = None,
        exclude: Set[str] = None,
        raise_validation_error: bool = False,
        queue: MutableSequence = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.mapper = mapper or NodeTypesMapper()
        self.context = context or {}
        self.include = include or set()
        self.exclude = exclude or set()
        self.raise_validation_error = raise_validation_error
        self.errors = []
        self.queue = queue

    def parser_for(self, *args: Any, **kwargs: Any) -> HTMLParser:
        return HTMLParser(target=self, strip_cdata=False, recover=True, remove_comments=True)

    def skip_node(self, node_name: str) -> bool:
        return self.include and node_name not in self.include or node_name in self.exclude

    def create_node_from_tag(self, tag: 'TagNode', node_type: NodeType = None) -> Optional[Node]:
        node_kind = tag.name
        if self.skip_node(node_kind):
            return None

        node_type = node_type or self.mapper.find_tag_node_type(tag)

        # Get & transform tag attributes
        node_attrs = node_type.prepare_attrs(tag.attrs)
        if node_type != self.mapper.default_node_type:
            node_kind = node_type.get_node_kind_value()
            if self.skip_node(node_kind):
                return None

        # Create node from class, collect/raise error
        try:
            node = node_type(kind=node_kind, **node_attrs)
        except ValidationError as exc:
            if self.raise_validation_error:
                raise exc
            self.errors.append(MarkupParserError(reason=exc, context=str(self)))
            return invalid_node(**node_attrs)

        # Pass outer context
        node.update_context(parent=tag.parent_node, **self.context)

        # node.children must be set as instance attribute, otherwise Pydantic uses iterators
        node.children = deque()

        # Add node post-init task to queue
        self.node_post_init(node)

        return node

    def recreate_tag_node(self, tag: 'TagNode', updated_node_type: NodeType) -> None:
        updated_node = self.create_node_from_tag(tag, updated_node_type)
        if not updated_node:
            return

        # No currently set node -> no update needed
        if not tag.node:
            tag.node = updated_node
            return

        updated_node.children = tag.node.children
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
        if self.queue is None:
            return
        task = node.post_init_method
        if task:
            self.queue.append(task)


class TagContents(deque):
    ref: Node

    def __init__(self, ref: Node):
        super().__init__()
        self.ref = ref

    def append(self, el: Union['TagNode', 'StringNode']) -> None:
        if el.node is not None:
            self.ref.children.append(el.node)
        super().append(el)


class TagNode(Tag):
    node: Optional[Node] = None
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
    def parent_node(self) -> Optional[Node]:
        parent_tag: TagNode = self.parent
        if parent_tag and parent_tag.name != 'body':
            return parent_tag.node


class StringNode(NavigableString):
    node: Optional[TextNode]

    def __new__(cls, value: str):  # type: ignore
        string = super().__new__(cls, value)
        string.node = TextNode.create(value) if value != '\n' else None
        return string


_ELEMENT_CLASSES = {Tag: TagNode, NavigableString: StringNode}
