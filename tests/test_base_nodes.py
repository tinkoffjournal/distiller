from faker import Faker
from pydantic import BaseModel
from pytest import mark

from distiller import Distilled
from distiller.nodes import RESERVED_NODE_ATTRS_NAMES, Node, TextNode, text

from .helpers import node_dict, text_dict

DEFAULT_NODE_KIND = Node.get_node_kind_value()


class Lead(Node):
    @classmethod
    def modify_attrs(cls, attrs: dict) -> None:
        attrs.update(modified=True)


class Nested(BaseModel):
    pax: int = 42


class Complex(Node):
    foo: str = 'bar'
    nested: Nested


def test_nodes_types_mapping():
    node = Node(children=[Lead(), TextNode(), Node(kind='some')])
    types = map(type, node.children)
    assert list(types) == [Lead, TextNode, Node]


def test_node_attrs_preparation():
    attrs = {
        'foo': 'bar',
        'kind': 'check',
        'pax': 42,
    }
    attrs_sanitized = Lead.prepare_attrs(attrs)
    for reserved in RESERVED_NODE_ATTRS_NAMES:
        assert reserved not in attrs_sanitized


def test_node_attrs_modification():
    attrs = {'modified': False}
    Lead.modify_attrs(attrs)
    assert attrs['modified']


def test_node_context():
    parent_node = Node(kind='parent')
    lead = Lead()
    lead.update_context(parent=parent_node, foo='bar')
    assert lead.context.parent == parent_node
    assert lead.context.data['foo'] == 'bar'


def test_node_schema():
    schema = Lead.schema()
    assert schema['title'] == Lead.__name__
    assert schema['properties']['allOf'] == {'$ref': f'#/definitions/{Node.__name__}'}


@mark.parametrize(
    'node,node_kind',
    [
        (Node(), DEFAULT_NODE_KIND),
        (Node(kind=None), DEFAULT_NODE_KIND),
        (Node(kind='custom_kind'), 'custom-kind'),
        (Lead(), Lead.get_node_kind_value()),
        (Lead(kind='foobar'), Lead.get_node_kind_value()),
    ],
    ids=['default', 'none_kind', 'custom_kind', 'custom_type', 'custom_type_override'],
)
def test_node_kind_setup(node, node_kind):
    assert node.kind == node_kind


def test_inner_object_serialization():
    node = Complex(nested=Nested(), foo='baaz')
    assert node.serialize() == node_dict(node.kind, nested=node.nested.dict(), foo='baaz')


def test_base_nodes_serialization(fake: Faker):
    # Paragraph-like node with single text child
    lead_text = fake.sentence()
    lead = Lead(children=[text(lead_text)])
    lead_dict = node_dict(lead.kind, text_dict(lead_text))
    assert lead.serialize() == lead_dict

    # Node with text & inline nodes
    text_before, text_inside, text_after = (fake.sentence() for _ in range(3))
    paragraph = Node(
        kind='p',
        children=[
            text(text_before),
            Node(kind='strong', children=[text(text_inside)]),
            text(text_after),
        ],
        foo='bar',
    )
    paragraph_dict = node_dict(
        paragraph.kind,
        text_dict(text_before),
        node_dict('strong', text_dict(text_inside)),
        text_dict(text_after),
        foo='bar',
    )
    assert paragraph.serialize() == paragraph_dict

    # All together now
    distilled = Distilled(nodes=[lead, paragraph])
    serialized = (
        lead_dict,
        paragraph_dict,
    )
    assert distilled.serialize()['nodes'] == serialized
