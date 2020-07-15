from distiller.nodes import Node
from distiller.base import DistilledObject
from asyncio import run


class Mutable(Node):
    modified: bool = False

    def post_init(self):
        self.modified = True
        return self


class AsyncMutable(Mutable):
    async def post_init(self):
        self.modified = True


def test_finalization():
    nodes_count = 3
    distilled = DistilledObject()
    distilled.nodes = [Mutable() for _ in range(nodes_count)]
    distilled.collect_tasks()
    tasks = list(distilled._tasks)
    assert len(tasks) == nodes_count
    results = list(distilled.run_tasks())
    assert all(map(lambda node: node.modified, distilled.nodes))
    assert len(results) == nodes_count


def test_async_finalization():
    distilled = DistilledObject()
    distilled.nodes = [AsyncMutable() for _ in range(3)]
    distilled.collect_tasks()
    run(distilled.finalize_async())
    assert all(map(lambda node: node.modified, distilled.nodes))
