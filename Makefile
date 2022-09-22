VENV	:= .venv
PYTHONPATH	:= $(dir $(abspath $(lastword $(MAKEFILE_LIST)))):$(shell echo $$PYTHONPATH)
PYTHON	:= PYTHONPATH=$(PYTHONPATH) $(VENV)/bin/python
PIP = $(VENV)/bin/pip

setup: $(VENV)/bin/activate 

web: $(VENV)/bin/activate
	( \
		source $(VENV)/bin/activate; \
		FLASK_APP=vegvisir-web FLASK_ENV=development flask run; \
	)

run: $(VENV)/bin/activate
	$(PYTHON) vegvisir-cli/app.py

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

clean:
	python3 -Bc "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
	python3 -Bc "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__')]"
	rm -rf $(VENV)
	rm -rf logs/*