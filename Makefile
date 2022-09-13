VENV	:= .venv
PYTHONPATH	:= $(dir $(abspath $(lastword $(MAKEFILE_LIST)))):$(shell echo $$PYTHONPATH)
PYTHON	:= PYTHONPATH=$(PYTHONPATH) $(VENV)/bin/python
PIP = $(VENV)/bin/pip
WORKING_DIRECTORY = $(shell pwd)

web:  $(VENV)/bin/activate npm-install
	@echo "Building frontend"
	@(  source $(VENV)/bin/activate;\
		cd vegvisirweb; npm run --silent build-only &> '/dev/null';)
	@echo "Running frontend"
	@(docker stop vegvisir-webui-nginx  &> '/dev/null' || true;\
		docker rm vegvisir-webui-nginx  &> '/dev/null' || true;\
		docker run --rm --name vegvisir-webui-nginx -v $(WORKING_DIRECTORY)/vegvisirweb/nginx_server/nginx.conf:/etc/nginx/nginx.conf:ro -v $(WORKING_DIRECTORY)/vegvisirweb/dist:/usr/share/nginx/html:ro -v $(WORKING_DIRECTORY)/vegvisirweb/nginx_server/default.conf:/etc/nginx/conf.d/default.conf:ro -p 8080:80 -d nginx &> '/dev/null';\
		) &
	@echo "Frontend available at: http://127.0.0.1:8080"
	@echo "Running backend"
	@( \
		source $(VENV)/bin/activate;\
		QUART_APP=vegvisirweb QUART_ENV=development quart run &> '/dev/null' || true;\
	) 
	@echo "Exiting: cleaning up"
	@(docker stop vegvisir-webui-nginx  &> '/dev/null' || true;\
		docker rm vegvisir-webui-nginx  &> '/dev/null' || true;)



web-dev: $(VENV)/bin/activate npm-install
	@echo "Running frontend"
	@(  source $(VENV)/bin/activate;\
		cd vegvisirweb; npm run --silent dev 2> '/dev/null' | head -n 4;) &
	@echo "Running backend"
	@( \
		source $(VENV)/bin/activate;\
		QUART_APP=vegvisirweb QUART_ENV=development quart run &> '/dev/null';\
	) 

run: $(VENV)/bin/activate
	$(PYTHON) vegvisir-cli/app.py

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

npm-install: 
	@echo 'Running npm install'
	@(cd vegvisirweb; npm install --silent)

clean:
	python3 -Bc "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
	python3 -Bc "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__')]"
	rm -rf $(VENV)
	rm -rf logs/*