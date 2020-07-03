from pytest import mark

from distiller.markup.preprocessor import compile_custom_tokens_patterns, tagify_custom_tokens

startchar = '['
endchar = ']'
closechar = '/'
basic_pattern, attrs_pattern = compile_custom_tokens_patterns(startchar, closechar, endchar)


@mark.parametrize(
    'markup,node_kind,node_attrs',
    [
        (f'Some text: {startchar}code{endchar} and other', 'code', ''),
        (f'Another {startchar}foo bar="baz" bax=1{endchar} wow', 'foo', ' bar="baz" bax=1'),
    ],
)
def test_patterns_compilation(markup, node_kind, node_attrs):
    assert basic_pattern.search('Plain text') is None
    assert basic_pattern.search(markup) is not None
    attrs_match = attrs_pattern.match(markup)
    if attrs_match is not None:
        assert attrs_match.groupdict()['name'] == node_kind
        assert attrs_match.groupdict()['attrs'] == node_attrs


@mark.parametrize(
    'token',
    [
        f'{startchar}foo2{endchar}',
        f'{startchar}foo.bar{endchar}',
        f'{startchar}{closechar} foo.bar{endchar}',
    ],
)
def test_invalid_tokens_parsing(token):
    assert attrs_pattern.match(token) is None


@mark.parametrize(
    'markup,expected',
    [
        ('[foo]', '<foo />'),
        ('[foo]Bar[/foo]', '<foo>Bar</foo>'),
        ('[foo]Bar[/ foo]', '<foo>Bar</foo>'),
        ('[foo]\nBar\n[/foo]', '<foo>\nBar\n</foo>'),
        ('Some square [foo2] brackets', 'Some square [foo2] brackets'),
        ('[foo-bar]', '<foo-bar />'),
        ('[foo_bar]', '<foo-bar />'),
        ('[foo_Bar]', '<foo-bar />'),
        ('[outer]Text [inner] more text[/outer]', '<outer>Text <inner /> more text</outer>'),
    ],
)
def test_tagify(markup, expected):
    assert (
        tagify_custom_tokens(markup, startchar, closechar, basic_pattern, attrs_pattern) == expected
    )
