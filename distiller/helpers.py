from html import escape
from inspect import getmodule, stack
from json import dumps as json_dumps
from re import UNICODE, compile as re_compile
from types import ModuleType
from typing import Any

from pydantic import ConstrainedStr
from pydantic.validators import strict_str_validator

# https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
CAMEL_CASE = re_compile(r'(?<!^)(?=[A-Z])')
MULTI_NEWLINES = re_compile(r'\n+')
MULTI_DASHES = re_compile(r'-+')
MULTI_SPACES = re_compile(r' +')
SOFTWRAPS = re_compile(r'[\u200c\u00ad]', UNICODE)
HTML_BREAK_ENTITIES = ('&shy;', '&zwnj;')
WHITESPACES = ('\N{NO-BREAK SPACE}', '&nbsp;')

# Used to split lines correctly when converting nodelist to plaintext
KNOWN_CONTAINER_KINDS = {'ul', 'ol', 'dl', 'div', 'table', 'tbody', 'section', 'header', 'footer'}


class NodeKind(ConstrainedStr):
    regex = re_compile(r'(^[a-z]+[a-z\d]?$)|(^[a-z][a-z-]+[a-z\d]$)')
    strip_whitespace = True

    def __new__(cls, value: str):  # type: ignore
        value = strict_str_validator(value)
        value = camel_to_kebab_case(value)
        # Replace underscores with hyphens to match HTML specification
        value = value.replace('_', '-')
        return MULTI_DASHES.sub('-', value)

    @classmethod
    def __modify_schema__(cls, field_schema: dict) -> None:
        field_schema.update(title='Distilled node kind')  # pragma: no cover


def camel_to_kebab_case(value: str) -> str:
    return CAMEL_CASE.sub('-', value).lower()


def glue_multi_newlines(markup: str) -> str:
    return MULTI_NEWLINES.sub('\n', markup)


def normalize_whitespace(text: str) -> str:
    text = SOFTWRAPS.sub('', text)
    for html_entity in HTML_BREAK_ENTITIES:
        text = text.replace(html_entity, '')
    for special_space_char in WHITESPACES:
        text = text.replace(special_space_char, ' ')
    return MULTI_SPACES.sub(' ', text).strip()


def current_module() -> ModuleType:
    parentframe = stack()[1][0]
    return getmodule(parentframe)  # type: ignore


def jsonify_node_value(value: Any) -> str:
    jsonified = json_dumps(value, ensure_ascii=False)
    jsonified = escape(jsonified.replace('\n', '\\n'))
    return jsonified
