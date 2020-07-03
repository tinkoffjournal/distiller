from pytest import mark, raises

from distiller import DistillerError, MarkupDistiller, Node
from distiller.helpers import current_module
from distiller.nodes import INVALID_NODE_KIND

from .helpers import node_dict


class Custom(Node):
    ...


class Foo(Node):
    bar: str = 'pax'


class Strict(Node):
    val: str


def test_preprocessors_applied(fake):
    distill = MarkupDistiller(preprocessors=[lambda markup: fake.bothify(markup)])
    result, _ = distill('????')
    assert '?' not in str(result.recursive_dict())


@mark.parametrize('config', ['[]', ('[', ']')])
def test_invalid_tagify_config(config):
    with raises(AssertionError):
        MarkupDistiller(tagify=config)


def test_empty_markup_parsing():
    result, errors = MarkupDistiller()('')
    assert result.recursive_dict()['nodes'] == ()
    assert errors == ()


def test_excluded_nodes():
    excluded = {'foo', 'bar'}

    def check_excluded(nodes):
        for node in nodes:
            if node['kind'] in excluded:
                assert False
            check_excluded(node.get('children', []))

    distill = MarkupDistiller(exclude=excluded, types_module=current_module())
    result, _ = distill('<p>Text[foo]</p><bar>')
    check_excluded(result.recursive_dict()['nodes'])


@mark.parametrize(
    'markup,expected',
    [
        ('[foo bar=baz]', [node_dict('foo', bar='baz')]),
        ('[foo]<bar>', [node_dict('foo'), node_dict('bar')]),
        ('[foo]<bar>[/foo]', [node_dict('foo', node_dict('bar'))]),
    ],
    ids=['single_tag', 'siblings', 'with_parent'],
)
def test_tagified_parsing(markup, expected):
    distill = MarkupDistiller(tagify='[/]')
    result, _ = distill(markup)
    assert list(result.recursive_dict()['nodes']) == expected


def test_invalid_nodes_parsing_no_raise():
    result, errors = MarkupDistiller(types_module=current_module())('<strict>')
    assert result.recursive_dict()['nodes'] == (node_dict(INVALID_NODE_KIND),)
    assert len(errors) > 0


def test_invalid_nodes_parsing_raise():
    with raises(DistillerError):
        MarkupDistiller(types_module=current_module())('<strict>', raise_validation_error=True)


def test_predefined_rules():
    distill = MarkupDistiller(types_module=current_module())
    result, _ = distill('<foo />')
    assert result.recursive_dict()['nodes'] == (node_dict('foo', bar='pax'),)


@mark.parametrize(
    'markup,rules,expected',
    [
        ('<foo class=bar>', {'foo.bar': Custom}, [node_dict('custom', **{'class': ['bar']})]),
        ('<bar /><baz />', {'bar': Custom}, [node_dict('custom'), node_dict('baz')]),
        ('<bar /><baz />', {'bar+baz': Custom}, [node_dict('bar'), node_dict('custom')]),
        ('<bar /><baz />', {'bar+baz.some': Custom}, [node_dict('bar'), node_dict('baz')]),
        (
            '<bar /><baz class=some />',
            {'bar+baz.some': Custom},
            [node_dict('bar'), node_dict('custom', **{'class': ['some']})],
        ),
    ],
    ids=[
        'classname',
        'tagname',
        'tag_siblings',
        'tag_siblings_classname_neg',
        'tag_siblings_classname_pos',
    ],
)
def test_mapping_css_rules(markup, rules, expected):
    result, _ = MarkupDistiller(rules=rules)(markup)
    assert list(result.recursive_dict()['nodes']) == expected
