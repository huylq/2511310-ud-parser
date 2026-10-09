PYTHON ?= python
BASE ?= project-02-base

.PHONY: test gate

test:
	$(PYTHON) -m pytest tests -q

gate:
	$(PYTHON) student-projects/_gate/gate.py 02-ud-parsing --base $(BASE)
