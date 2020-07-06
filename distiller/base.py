from types import ModuleType
from typing import Any, Callable, Dict, Iterable, MutableSequence, Sequence, Set, Tuple, Type

from pydantic import BaseModel, Field
from pydantic.schema import schema

from .nodes import (
    AnyNode,
    NodeType,
    deserialize_nodelist,
    load_nodes_types_from_module,
    nodelist_to_html,
)

DistillerError = ValueError
DistillationResult = Tuple['DistilledObject', Sequence[DistillerError]]


class BaseDistiller:
    include: Set[str]
    exclude: Set[str]
    return_type: Type['DistilledObject']
    registry: 'Registry'

    class Registry(Set[NodeType]):
        def indexed(self) -> Dict[str, NodeType]:
            return {node_type.get_node_kind_value(): node_type for node_type in self}

    def __init__(
        self,
        types_module: ModuleType = None,
        return_type: Type['DistilledObject'] = None,
        include: Iterable[str] = None,
        exclude: Iterable[str] = None,
    ):
        self.registry = self.Registry(load_nodes_types_from_module(types_module))
        self.return_type = return_type or DistilledObject
        assert issubclass(
            self.return_type, DistilledObject
        ), 'Distiller return type must be subclassed from DistilledObject'
        self.include = set(include or ())
        self.exclude = set(exclude or ())

    def __call__(
        self, source: Any, context: Dict[str, Any] = None, raise_validation_error: bool = False,
    ) -> DistillationResult:
        ...  # pragma: no cover

    def schema(self, title: str = None, description: str = None) -> Dict[str, Any]:
        return schema(
            self.registry, title=title, description=description  # type: ignore
        )

    def deserialize(
        self, nodes: Iterable[Dict[str, Any]], finalize_nodes: bool = False
    ) -> 'DistilledObject':
        deserialized = deserialize_nodelist(nodes, types_index=self.registry.indexed())
        return DistilledObject.construct(
            nodes=tuple(deserialized) if finalize_nodes else deserialized
        )


class DistilledObject(BaseModel):
    nodes: Iterable[AnyNode] = Field(default=(), title='Distilled body')

    def serialize(self, **kwargs: Any) -> Dict[str, Any]:
        serialized = self.dict(exclude={'nodes'})
        nodes = tuple(node.serialize(**kwargs) for node in self.nodes)
        return {**serialized, 'nodes': nodes}

    def to_html(self) -> str:
        return nodelist_to_html(self.nodes)

    @property
    def _tasks(self) -> Iterable[Callable]:
        return filter(callable, self._State.tasks)

    def __call__(self) -> None:
        for task in self._tasks:
            task()
        self._State.finalized = True

    class Config:
        title = 'Distilled object'

    class _State:
        finalized: bool = False
        tasks: 'DistilledObjectTasks' = []


DistilledObjectTasks = MutableSequence[Callable]


class UnsupportedMarkupDistiller:  # pragma: no cover
    def __init__(self, *args: Any, **kwargs: Any):
        raise RuntimeError('BeautifulSoup must be installed to use MarkupDistiller')
