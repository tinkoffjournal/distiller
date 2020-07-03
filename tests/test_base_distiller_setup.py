from sys import modules

from distiller.base import BaseDistiller
from distiller.helpers import current_module
from distiller.nodes import Node, load_nodes_types_from_module


class Foo(Node):
    ...


class Bar(Node):
    ...


NODES = {Foo, Bar}
distill = BaseDistiller(types_module=current_module())


def test_types_loading():
    nodes_types = set(load_nodes_types_from_module(modules[__name__]))
    assert nodes_types == NODES


def test_distiller_registry_init():
    assert distill.registry == NODES


def test_distiller_schema_init():
    schema = distill.schema()
    for node_type in NODES:
        assert node_type.__name__ in schema.get('definitions', {})
