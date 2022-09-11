VENV	:= .venv
PYTHONPATH	:= $(dir $(abspath $(lastword $(MAKEFILE_LIST)))):$(shell echo $$PYTHONPATH)
PYTHON	:= PYTHONPATH=$(PYTHONPATH) $(VENV)/bin/python
PIP = $(VENV)/bin/pip
WORKING_DIRECTORY = $(shell pwd)

web: $(VENV)/bin/activate
	(  source $(VENV)/bin/activate;\
		cd vegvisirweb; npm i; npm run --silent build &> '/dev/null';\
		docker stop vegvisir-webui-nginx;\
		docker rm vegvisir-webui-nginx;\
		docker run --rm --name vegvisir-webui-nginx -v $(WORKING_DIRECTORY)/vegvisirweb/nginx_server/nginx.conf:/etc/nginx/nginx.conf:ro -v $(WORKING_DIRECTORY)/vegvisirweb/dist:/usr/share/nginx/html:ro -v $(WORKING_DIRECTORY)/vegvisirweb/nginx_server/default.conf:/etc/nginx/conf.d/default.conf:ro -p 8080:80 -d nginx;\
		) &
	( \
		source $(VENV)/bin/activate;\
		QUART_APP=vegvisirweb QUART_ENV=development quart run;\
	) 

web-dev: $(VENV)/bin/activate
	
	(  source $(VENV)/bin/activate;\
		cd vegvisirweb; npm run --silent dev | head -n 5;) &
	( \
		sleep 5;\
		source $(VENV)/bin/activate;\
		QUART_APP=vegvisirweb QUART_ENV=development quart run;\
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