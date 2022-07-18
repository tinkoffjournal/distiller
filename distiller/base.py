from types import ModuleType
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    Iterator,
    MutableSequence,
    Sequence,
    Set,
    Tuple,
    Type,
)

from pydantic import BaseModel, Field
from pydantic.schema import schema

from .nodes import (
    AllowedAttrs,
    AnyNode,
    NodeType,
    deserialize_nodelist,
    load_nodes_types_from_module,
    nodelist_to_html,
    nodelist_to_plaintext,
    serialize_nodelist,
)

DistillerError = ValueError
DistillationResult = Tuple['DistilledObject', Sequence[DistillerError]]


class BaseDistiller:
    include: Set[str]
    exclude: Set[str]
    return_type: Type['DistilledObject']
    registry: 'Registry'
    context: Dict[str, Any]

    class Registry(Set[NodeType]):
        def indexed(self) -> Dict[str, NodeType]:
            return {node_type.get_node_kind_value(): node_type for node_type in self}

    def __init__(
        self,
        types_module: ModuleType = None,
        return_type: Type['DistilledObject'] = None,
        include: Iterable[str] = None,
        exclude: Iterable[str] = None,
        context: Dict[str, Any] = None,
    ):
        self.registry = self.Registry(load_nodes_types_from_module(types_module))
        self.return_type = return_type or DistilledObject
        assert issubclass(
            self.return_type, DistilledObject
        ), 'Distiller return type must be subclassed from DistilledObject'
        self.include = set(include or ())
        self.exclude = set(exclude or ())
        self.context = context or {}

    def __call__(
        self,
        source: Any,
        context: Dict[str, Any] = None,
        raise_validation_error: bool = False,
    ) -> DistillationResult:
        ...  # pragma: no cover

    def schema(self, title: str = None, description: str = None) -> Dict[str, Any]:
        return schema(self.registry, title=title, description=description)  # type: ignore

    def deserialize(
        self,
        nodes: Iterable[Dict[str, Any]],
        finalize_nodes: bool = False,
        context: Dict[str, Any] = None,
        **values: Any,
    ) -> 'DistilledObject':
        deserialized = deserialize_nodelist(
            nodes, types_index=self.registry.indexed(), context=context
        )
        return self.return_type.construct(
            nodes=tuple(deserialized) if finalize_nodes else deserialized, **values
        )


class DistilledObject(BaseModel):
    nodes: Iterable[AnyNode] = Field(default=(), title='Distilled body')

    def serialize(self, **kwargs: Any) -> Dict[str, Any]:
        serialized = self.dict(exclude={'nodes'})
        nodes = serialize_nodelist(self.nodes, **kwargs)
        return {**serialized, 'nodes': tuple(nodes)}

    def to_html(
        self,
        include: Set[str] = None,
        exclude: Set[str] = None,
        exclude_invalid: bool = True,
        allowed_attrs: AllowedAttrs = None,
    ) -> str:
        return nodelist_to_html(
            self.nodes,
            include=include,
            exclude=exclude,
            exclude_invalid=exclude_invalid,
            allowed_attrs=allowed_attrs,
        )

    def to_plaintext(
        self,
        delimiter: str = '\n\n',
        include: Set[str] = None,
        exclude: Set[str] = None,
    ) -> str:
        return nodelist_to_plaintext(
            self.nodes, delimiter=delimiter, include=include, exclude=exclude
        )

    @property
    def _tasks(self) -> Iterable[Callable]:
        return filter(callable, self._State.tasks)

    def collect_tasks(self, nodes: Iterable[AnyNode] = None) -> None:
        for node in nodes or self.nodes:
            task = getattr(node, 'post_init_method', None)
            if task:
                self._State.tasks.append(task)
            subnodes = getattr(node, 'children', [])
            if subnodes:
                self.collect_tasks(subnodes)

    def run_tasks(self) -> Iterator[Any]:
        for task in self._tasks:
            result = task()
            if result:
                yield result

    def finalize(self) -> None:
        for _ in self.run_tasks():
            pass
        self._State.finalized = True

    async def run_tasks_async(self) -> AsyncIterator[Any]:
        for task_result in self.run_tasks():
            if isinstance(task_result, Awaitable):
                task_result = await task_result
            if task_result:
                yield task_result

    async def finalize_async(self) -> None:
        async for _ in self.run_tasks_async():
            pass
        self._State.finalized = True

    class Config:
        title = 'Distilled object'

    class _State:
        finalized: bool = False
        parser: Any = None
        tasks: 'DistilledObjectTasks' = []


DistilledObjectTasks = MutableSequence[Callable]


class UnsupportedMarkupDistiller:  # pragma: no cover
    def __init__(self, *args: Any, **kwargs: Any):
        raise RuntimeError('BeautifulSoup must be installed to use MarkupDistiller')
