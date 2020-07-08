from bs4 import BeautifulSoup
from pydantic import BaseModel

from distiller.base import DistilledObject
from distiller.helpers import jsonify_node_value
from distiller.nodes import INVALID_NODE_KIND, InvalidNode, Node, text


class Bogus(BaseModel):
    lorem: str = 'ipsum'
    spqr: bool = True


class CoolNode(Node):
    foo: str = 'bar'
    pax: int = 42
    this: bool = True
    that: bool = False
    items: list = ['such', 'wow', 10]
    mapping: dict = {'hip': 'hop'}
    bogus: Bogus


class SimpleNode(Node):
    this: str


test_node = CoolNode(bogus=Bogus())


def test_single_node_html():
    list_value = jsonify_node_value(test_node.items)
    dict_value = jsonify_node_value(test_node.mapping)
    nested_model_value = jsonify_node_value(test_node.bogus.dict())
    html = (
        f'<{test_node.kind} foo="bar" pax="42" items="{list_value}" '
        f'mapping="{dict_value}" bogus="{nested_model_value}" this />'
    )
    assert test_node.to_html() == html


def test_node_children_html():
    node = SimpleNode(children=[test_node], this='that')
    assert node.to_html() == f'<{node.kind} this="that">{test_node.to_html()}</{node.kind}>'


def test_mixed_nodes_structure():
    text_content = 'bogus'
    distilled = DistilledObject(nodes=[test_node, text(text_content), InvalidNode(tagname='some')])
    assert distilled.to_html() == test_node.to_html() + text_content + f'<{INVALID_NODE_KIND} />'


def test_distilled_object_html():
    test_child = SimpleNode(children=[CoolNode(bogus=Bogus())], this='that')
    distilled = DistilledObject(nodes=(test_child for _ in range(3)))
    assert distilled.to_html() == ''.join((test_child.to_html() for _ in range(3)))


def test_invalid_node_html():
    node = SimpleNode(this='other')
    node.kind = ''
    assert node.to_html() == ''


def test_distilled_to_html_conditionals():
    simple = SimpleNode(this='this')
    distilled = DistilledObject(
        nodes=[
            test_node,
            SimpleNode(this='this'),
            Node(kind='bar', children=[SimpleNode(this='that')]),
            test_node,
            Node(kind='foo'),
        ]
    )
    distilled.nodes = tuple(distilled.nodes)
    html_exc = distilled.to_html(exclude={simple.kind, 'foo'})
    soup = BeautifulSoup(html_exc, features='lxml')
    assert len(soup.find_all(simple.kind)) == 0
    assert len(soup.find_all('foo')) == 0
    allowed_kinds = {test_node.kind, simple.kind}
    html_inc = distilled.to_html(include=allowed_kinds)
    soup = BeautifulSoup(html_inc, features='lxml')
    found_kinds = set()
    for tag in soup.body.descendants:
        found_kinds.add(tag.name)
    assert allowed_kinds == found_kinds
