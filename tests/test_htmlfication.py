from json import dumps as json_dumps

from pydantic import BaseModel

from distiller.base import DistilledObject
from distiller.nodes import INVALID_NODE_KIND, InvalidNode, Node, text

from .helpers import make_soup


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


def test_node_attrs_htmlfication():
    tag = make_soup(test_node.to_html()).find(test_node.kind)
    assert tag.name == test_node.kind
    assert tag['pax'] == str(test_node.pax)
    assert tag['this'] == ''
    assert 'that' not in tag
    assert tag['items'] == json_dumps(test_node.items, ensure_ascii=False)
    assert tag['mapping'] == json_dumps(test_node.mapping, ensure_ascii=False)
    assert tag['bogus'] == test_node.bogus.json()


def test_mixed_nodes_structure():
    text_content = 'bogus'
    distilled = DistilledObject(nodes=[test_node, text(text_content), InvalidNode(tagname='some')])
    distilled.nodes = tuple(distilled.nodes)
    assert distilled.to_html(exclude_invalid=False) == test_node.to_html() + text_content + f'<{INVALID_NODE_KIND} />'
    assert distilled.to_html(exclude_invalid=True) == test_node.to_html() + text_content


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
    soup = make_soup(html_exc)
    assert len(soup.find_all(simple.kind)) == 0
    assert len(soup.find_all('foo')) == 0
    allowed_kinds = {test_node.kind, simple.kind}
    html_inc = distilled.to_html(include=allowed_kinds)
    soup = make_soup(html_inc)
    found_kinds = set()
    for tag in soup.body.descendants:
        found_kinds.add(tag.name)
    assert allowed_kinds == found_kinds


def test_strict_nodes_attrs():
    distilled = DistilledObject(
        nodes=[
            test_node,
            Node(kind='bar', children=[test_node]),
            Node(kind='foo', rel='baz', name='other'),
        ]
    )
    allowed_attrs = {'cool-node': {'pax', 'this'}, 'foo': {'rel'}}
    html = distilled.to_html(allowed_attrs=allowed_attrs)
    soup = make_soup(html)
    for tag in soup.body.descendants:
        allowed_tag_attrs = allowed_attrs.get(tag.name, set())
        assert set(tag.attrs.keys()) == allowed_tag_attrs
