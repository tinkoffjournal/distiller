.DEFAULT_GOAL := format
DIR = distiller

format:
	isort $(DIR)
	black $(DIR)

type:
	mypy $(DIR)

lint:
	isort --check-only --diff $(DIR)
	black --check $(DIR)
	flake8 $(DIR)

test:
	pytest -vv

cov:
	pytest --cov=$(DIR) --cov-report term-missing:skip-covered

check:
	make lint
	make type

FILE = index
play:
	python -m tests.playground $(FILE)
