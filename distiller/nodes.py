from inspect import getmembers, isclass
from types import ModuleType
from typing import Any, Callable, Dict, Iterator, MutableSequence, NamedTuple, Optional, Type, Union

from pydantic import BaseModel, Extra, Field, NoneStr, validator

from .helpers import NodeKind

RESERVED_NODE_ATTRS_NAMES = {'kind', 'children'}
DEFAULT_NODE_SCHEMA_TITLE = 'Distilled node'
TEXT_NODE_KIND = NodeKind('text')
INVALID_NODE_KIND = NodeKind('invalid-node')


class NodeContext(NamedTuple):
    parent: Optional['Node'] = None
    data: Dict[str, Any] = {}


class BaseNode(BaseModel):
    kind: NodeKind


class Node(BaseNode):
    kind: NodeKind = Field(default=None, title='Distilled node kind')
    children: 'NodeChildren' = Field(default=[], title='Distilled subnodes')

    # Custom kind value may be set only for base nodes without specific schema,
    # otherwise class name is used
    @validator('kind', pre=True, always=True)
    def set_node_kind(cls, value: NoneStr) -> NodeKind:
        if value is not None and cls is Node:  # type: ignore
            return NodeKind(value)
        return cls.get_node_kind_value()

    def recursive_dict(self, **kwargs: Any) -> Dict[str, Any]:
        return dictify_recursively(self, **kwargs)

    @classmethod
    def get_node_kind_value(cls) -> NodeKind:
        return NodeKind(cls.__name__)

    @classmethod
    def prepare_attrs(cls, attrs: Dict[str, Any]) -> Dict[str, Any]:
        attrs = {
            attr_name: attr
            for attr_name, attr in attrs.items()
            if attr_name not in RESERVED_NODE_ATTRS_NAMES
        }
        cls.modify_attrs(attrs)
        return attrs

    @classmethod
    def modify_attrs(cls, attrs: Dict[str, Any]) -> None:
        ...  # pragma: no cover

    @property
    def post_init_method(self) -> Optional[Callable]:
        method = getattr(self, 'post_init', None)
        return method if callable(method) else None

    @property
    def context(self) -> NodeContext:
        return self._State.context

    def update_context(self, parent: 'Node' = None, **kwargs: Any) -> NodeContext:
        ctx = NodeContext(
            parent=parent or self._State.context.parent,
            data={**self._State.context.data, **kwargs},
        )
        self._State.context = ctx
        return ctx

    class _State:
        context: NodeContext = NodeContext()

    class Config:
        @staticmethod
        def _modify_node_schema(schema: Dict[str, Any], model: 'NodeType') -> None:
            title = schema.get('title', None)
            if title in {DEFAULT_NODE_SCHEMA_TITLE, None}:
                title = model.__name__
            properties = schema.get('properties', {})
            if model is not Node:
                properties = {
                    prop: schema
                    for prop, schema in properties.items()
                    if prop not in RESERVED_NODE_ATTRS_NAMES
                }
                properties['allOf'] = {'$ref': f'#/definitions/{Node.__name__}'}
            schema.update(title=title, properties=properties)

        title = DEFAULT_NODE_SCHEMA_TITLE
        extra = Extra.allow
        schema_extra = _modify_node_schema


class TextNode(BaseNode):
    kind: NodeKind = Field(default=TEXT_NODE_KIND, const=True)
    content: str = Field(default='', title='Text node inner content')

    @classmethod
    def create(cls, text: str) -> 'TextNode':
        return cls(content=text.strip('\n'))

    class Config:
        title = 'Text node'
        extra = Extra.forbid

    def __str__(self) -> str:
        return self.content

    def __repr__(self) -> str:
        return self.__str__()


def text(content: str = '') -> TextNode:
    return TextNode(content=content)


def invalid_node(**attrs: Any) -> Node:
    return Node(kind=INVALID_NODE_KIND)


AnyNode = Union[TextNode, Node]
NodeChildren = MutableSequence[AnyNode]
NodeType = Type[Node]

Node.update_forward_refs()


def dictify_recursively(node: AnyNode, **kwargs: Any) -> Dict[str, Any]:
    if isinstance(node, TextNode):
        return node.dict()
    exclude = kwargs.get('exclude') or set()
    kwargs.update(exclude=exclude.union({'children'}))
    children = map(lambda child: dictify_recursively(child, **kwargs), node.children)
    return {**node.dict(**kwargs), 'children': tuple(children)}


def load_nodes_types_from_module(module: Optional[ModuleType]) -> Iterator[NodeType]:
    for _, node_type in getmembers(module, is_node_type):
        yield node_type


def is_node_type(obj: Any) -> bool:
    return isclass(obj) and issubclass(obj, Node) and obj is not Node
