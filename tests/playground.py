from argparse import ArgumentParser
from pathlib import Path

from devtools import debug

from distiller import MarkupDistiller

argparser = ArgumentParser()
argparser.add_argument('file')
args = argparser.parse_args()
distill = MarkupDistiller(tagify='[/]')


def play() -> None:
    markup = Path(f'tests/data/{args.file}.html').read_text()
    distilled, errors = distill(markup)
    for node in distilled.nodes:
        debug(node)
    if errors:
        debug(errors)


if __name__ == '__main__':
    play()
