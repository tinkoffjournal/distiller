from bs4 import BeautifulSoup

from distiller.nodes import TEXT_NODE_KIND


def node_dict(kind: str, *children: dict, **attrs) -> dict:
    if children:
        attrs.update(children=children)
    return {'kind': kind, **attrs}


def text_dict(content: str) -> dict:
    return {'kind': TEXT_NODE_KIND, 'content': content}


def make_soup(markup: str) -> BeautifulSoup:
    return BeautifulSoup(markup, features='lxml')
