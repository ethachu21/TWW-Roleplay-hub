.PHONY: install start

.venv:
	python -m venv .venv

install: .venv requirements.txt
	.venv/bin/pip install -r requirements.txt

start: install
	.venv/bin/python main.py
