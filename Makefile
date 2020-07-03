.DEFAULT_GOAL := fmt
DIR = distiller

fmt:
	isort --recursive $(DIR)
	black $(DIR)

type:
	mypy $(DIR)

lint:
	isort --recursive --check-only --diff $(DIR)
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
