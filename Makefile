PY=python
PIP=pip

.PHONY: run check test lint type fmt

run:
	$(PY) -m odoo_mcp.mcp_server

check: lint type test

lint:
	ruff check .

fmt:
	ruff format .

type:
	mypy src tests

test:
	pytest -q

