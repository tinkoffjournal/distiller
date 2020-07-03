from pydantic import ValidationError
from pydantic.errors import StrError
from pytest import mark, raises

from distiller import Node
from distiller.helpers import NodeKind, glue_multi_newlines


@mark.parametrize(
    'value,expected',
    [
        ('P', 'p'),
        ('ul', 'ul'),
        ('NodeType', 'node-type'),
        ('node_type', 'node-type'),
        ('node_Type', 'node-type'),
    ],
    ids=['p', 'ul', 'camel_case', 'snake_case', 'mixed_case'],
)
def test_node_kind_value_autoformatting(value, expected):
    assert NodeKind(value) == expected


@mark.parametrize('value', [42, object(), None], ids=['int', 'obj', 'none'])
def test_invalid_node_kind_type(value):
    with raises(StrError):
        NodeKind(value)


@mark.parametrize(
    'value',
    ['', 'элемент', 'node.2[', '-node-kind', 'node_bar_'],
    ids=['empty', 'non_latin', 'not_allowed_chars', 'trailing_start', 'trailing_end'],
)
def test_invalid_node_kind_value(value):
    with raises(ValidationError):
        Node(kind=value)


def test_multiple_newlines_are_glued():
    assert glue_multi_newlines('foo\n\n\nbar\n') == 'foo\nbar\n'
