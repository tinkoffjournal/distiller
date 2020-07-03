from inspect import getmodule, stack
from re import compile as re_compile
from types import ModuleType

from pydantic import ConstrainedStr
from pydantic.validators import strict_str_validator

# https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
CAMEL_CASE = re_compile(r'(?<!^)(?=[A-Z])')
MULTI_NEWLINES = re_compile(r'\n+')
MULTI_DASHES = re_compile(r'-+')


class NodeKind(ConstrainedStr):
    regex = re_compile(r'(^[a-z]+$)|(^[a-z][a-z-]+[a-z]$)')
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


def current_module() -> ModuleType:
    parentframe = stack()[1][0]
    return getmodule(parentframe)  # type: ignore
