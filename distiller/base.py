from types import ModuleType
from typing import Any, Callable, Dict, Iterable, MutableSequence, Sequence, Set, Tuple, Type

from pydantic import BaseModel, Field
from pydantic.schema import schema

from .nodes import AnyNode, NodeType, dictify_recursively, load_nodes_types_from_module

DistillerError = ValueError
DistillationResult = Tuple['DistilledObject', Sequence[DistillerError]]


class BaseDistiller:
    include: Set[str]
    exclude: Set[str]
    return_type: Type['DistilledObject']
    registry: Set[NodeType]

    def __init__(
        self,
        types_module: ModuleType = None,
        return_type: Type['DistilledObject'] = None,
        include: Iterable[str] = None,
        exclude: Iterable[str] = None,
    ):
        self.registry = set(load_nodes_types_from_module(types_module))
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


class DistilledObject(BaseModel):
    nodes: Iterable[AnyNode] = Field(default=(), title='Distilled body')

    def recursive_dict(self, **kwargs: Any) -> Dict[str, Any]:
        dictified = self.dict(exclude={'nodes'})
        nodes = tuple(dictify_recursively(node, **kwargs) for node in self.nodes)
        return {**dictified, 'nodes': nodes}

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
