VENV	:= .venv
PYTHONPATH	:= $(dir $(abspath $(lastword $(MAKEFILE_LIST)))):$(shell echo $$PYTHONPATH)
PYTHON	:= PYTHONPATH=$(PYTHONPATH) $(VENV)/bin/python
PIP = $(VENV)/bin/pip

web: $(VENV)/bin/activate
	( \
		source $(VENV)/bin/activate; \
		FLASK_APP=vegvisir-web FLASK_ENV=production flask run;\
	) &
	cd vegvisir-web; npm run dev;

	

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