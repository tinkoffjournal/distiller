from distiller.base import DistilledObject
from distiller.helpers import normalize_whitespace
from distiller.nodes import InvalidNode, node as el, text as _

simple_plaintext = '''Hello, world.

OK:

1st

2nd

3rd

Bare text.'''


def test_simple_plaintext():
    bare_text = 'Bare text.'
    distilled = DistilledObject(
        nodes=[
            el('lead', _('Hello, '), el('b', _('world.'))),
            el(
                'div',
                *[
                    el('p', _('OK:')),
                    el('ul', *[el('li', _('1st')), el('li', _('2nd')), el('li', _('3rd')),]),
                ],
            ),
            InvalidNode(tagname='any'),
            _(bare_text),
        ]
    )
    assert distilled.to_plaintext() == simple_plaintext


def test_whitespace_normalization():
    test_string = 'Some&nbsp;text  content with spe&shy;cialties\n'
    assert normalize_whitespace(test_string) == 'Some text content with specialties'
