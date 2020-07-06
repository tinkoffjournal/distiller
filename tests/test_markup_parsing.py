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


class Boolean(Node):
    enabled: bool = False


def test_preprocessors_applied(fake):
    distill = MarkupDistiller(preprocessors=[lambda markup: fake.bothify(markup)])
    result, _ = distill('????')
    assert '?' not in str(result.serialize())


def test_postprocessors_applied():
    def postprocessor(node: Node) -> None:
        node.bar = 'MODIFIED'

    distill = MarkupDistiller(postprocessors=[postprocessor])
    distilled, _ = distill('<foo /><bar /><baz />')
    assert all(map(lambda node: node.bar == 'MODIFIED', distilled.nodes))


@mark.parametrize('config', ['[]', ('[', ']')])
def test_invalid_tagify_config(config):
    with raises(AssertionError):
        MarkupDistiller(tagify=config)


def test_empty_markup_parsing():
    result, errors = MarkupDistiller()('')
    assert result.serialize()['nodes'] == ()
    assert errors == ()


@mark.parametrize(
    'markup,expected',
    [
        ('<boolean />', False),
        ('<boolean enabled />', True),
        ('<boolean enabled=true />', True),
        ('<boolean enabled=any />', True),
        ('<boolean enabled=false />', False),
    ],
    ids=['default_value', 'no_value', 'true_value', 'any_value', 'false_value'],
)
def test_positional_html_attrs(markup, expected):
    result, _ = MarkupDistiller(types_module=current_module())(markup)
    assert result.nodes[0].enabled == expected


def test_excluded_nodes():
    excluded = {'foo', 'bar'}

    def check_excluded(nodes):
        for node in nodes:
            if node['kind'] in excluded:
                assert False
            check_excluded(node.get('children', []))

    distill = MarkupDistiller(exclude=excluded, types_module=current_module())
    result, _ = distill('<p>Text[foo]</p><bar>')
    check_excluded(result.serialize()['nodes'])


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
    assert list(result.serialize()['nodes']) == expected


def test_invalid_nodes_parsing_no_raise():
    result, errors = MarkupDistiller(types_module=current_module())('<strict>')
    assert result.serialize()['nodes'] == (node_dict(INVALID_NODE_KIND, tagname='strict'),)
    assert len(errors) > 0


def test_invalid_nodes_parsing_raise():
    with raises(DistillerError):
        MarkupDistiller(types_module=current_module())('<strict>', raise_validation_error=True)


def test_predefined_rules():
    distill = MarkupDistiller(types_module=current_module())
    result, _ = distill('<foo />')
    assert result.serialize()['nodes'] == (node_dict('foo', bar='pax'),)


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
    assert list(result.serialize()['nodes']) == expected
