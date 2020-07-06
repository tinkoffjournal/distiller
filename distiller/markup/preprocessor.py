import re
from collections import deque
from typing import Deque, Pattern, Tuple

from ..helpers import NodeKind


def tagify_custom_tokens(
    markup: str,
    start_char: str,
    close_char: str,
    token_pattern: Pattern,
    token_attrs_pattern: Pattern,
) -> str:
    bits: Deque[str] = deque()
    closing_tokens_stack: Deque[str] = deque()

    for bit in reversed(token_pattern.split(markup)):
        if not bit:
            continue

        is_closing = False
        is_self_closing = False

        # Non-tokenized particle
        if not bit.startswith(start_char):
            bits.appendleft(bit)
            continue

        # Extract token name
        token_attrs_match = token_attrs_pattern.match(bit)
        if not token_attrs_match:
            bits.appendleft(bit)
            continue
        token_dict = token_attrs_match.groupdict()
        token_name = NodeKind(token_dict['name'])
        token_attrs = token_dict.get('attrs') or ''

        # Closing shortcode
        if bit.startswith(f'{start_char}{close_char}'):
            is_closing = True
            closing_tokens_stack.appendleft(token_name)

        # Self-closing shortcode
        elif not closing_tokens_stack or closing_tokens_stack[0] != token_name:
            is_self_closing = True

        # Opening shortcode
        else:
            closing_tokens_stack.popleft()

        opener = '</' if is_closing else '<'
        closer = ' />' if is_self_closing else '>'
        tag = f'{opener}{token_name}{token_attrs}{closer}'
        bits.appendleft(tag)

    return ''.join(bits)


TOKEN_NAME_CHARS = r'[a-zA-Z_-]'
TOKEN_BASIC_PATTERN = r'({start}.+?{end})'
TOKEN_ATTRS_PATTERN = r'^{start}{close}?\s?(?P<name>{valid_name_chars}+)(?P<attrs>\s.*?)?{end}$'


def compile_custom_tokens_patterns(
    start_char: str, close_char: str, end_char: str
) -> Tuple[Pattern, Pattern]:
    basic_pattern = re.compile(
        TOKEN_BASIC_PATTERN.format(start=re.escape(start_char), end=re.escape(end_char)),
        flags=re.DOTALL,
    )
    attrs_pattern = re.compile(
        TOKEN_ATTRS_PATTERN.format(
            start=re.escape(start_char),
            end=re.escape(end_char),
            close=re.escape(close_char),
            valid_name_chars=TOKEN_NAME_CHARS,
        ),
        flags=re.DOTALL,
    )
    return basic_pattern, attrs_pattern
