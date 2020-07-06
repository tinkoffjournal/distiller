from sys import modules
from typing import Iterator

from distiller.base import BaseDistiller, DistilledObject
from distiller.helpers import current_module
from distiller.nodes import (
    INVALID_NODE_KIND,
    InvalidNode,
    Node,
    TextNode,
    load_nodes_types_from_module,
)

from .helpers import node_dict


class Foo(Node):
    ...


class Bar(Node):
    pax: int = 42


NODES = {Foo, Bar}
distill = BaseDistiller(types_module=current_module())


def test_types_loading():
    nodes_types = set(load_nodes_types_from_module(modules[__name__]))
    assert nodes_types == NODES


def test_distiller_registry_init():
    assert distill.registry == NODES
    assert distill.registry.indexed() == {
        node_type.get_node_kind_value(): node_type for node_type in NODES
    }


def test_distiller_schema_init():
    schema = distill.schema()
    for node_type in NODES:
        assert node_type.__name__ in schema.get('definitions', {})


def test_distiller_deserialization():
    distilled = DistilledObject(
        nodes=[Foo(children=[Bar()]), TextNode(content='some'), InvalidNode(tagname='any')]
    )
    distilled_dict = distilled.serialize()
    redistilled_lazy = distill.deserialize(nodes=distilled_dict['nodes'], finalize_nodes=False)
    assert isinstance(redistilled_lazy.nodes, Iterator)
    redistilled = distill.deserialize(nodes=distilled_dict['nodes'], finalize_nodes=True)
    redistilled_dict = redistilled.serialize()
    assert list(map(type, redistilled.nodes)) == [Foo, TextNode, InvalidNode]
    assert distilled_dict == redistilled_dict


def test_incomplete_deserialized_items():
    data = [node_dict('', foo='bar'), node_dict(INVALID_NODE_KIND)]
    redistilled = distill.deserialize(data)
    assert len(list(redistilled.nodes)) == 0
