VENV	:= .venv
PYTHONPATH	:= $(dir $(abspath $(lastword $(MAKEFILE_LIST)))):$(shell echo $$PYTHONPATH)
PYTHON	:= PYTHONPATH=$(PYTHONPATH) $(VENV)/bin/python
PIP = $(VENV)/bin/pip
WORKING_DIRECTORY = $(shell pwd)
PASSWORD ?= $(shell bash -c 'read -s -p "Please enter sudo password: " pwd; echo $$pwd')

web: $(VENV)/bin/activate
	@(  echo 'Vegvisir: npm installing packages';\
		cd vegvisirweb; npm i &>> '$(WORKING_DIRECTORY)/vegvisir_application_logs/npm.txt';)
	@(	echo 'Vegvisir: npm building frontend';\
		cd vegvisirweb; npm run --silent build-only &>> '$(WORKING_DIRECTORY)/vegvisir_application_logs/npm.txt') 
	@(echo 'Vegvisir: running frontend';\
		docker stop vegvisir-webui-nginx &>> '$(WORKING_DIRECTORY)/vegvisir_application_logs/docker.txt';\
		docker rm vegvisir-webui-nginx &>> '$(WORKING_DIRECTORY)/vegvisir_application_logs/docker.txt';\
		docker run --rm --name vegvisir-webui-nginx -v $(WORKING_DIRECTORY)/vegvisirweb/nginx_server/nginx.conf:/etc/nginx/nginx.conf:ro -v $(WORKING_DIRECTORY)/vegvisirweb/dist:/usr/share/nginx/html:ro -v $(WORKING_DIRECTORY)/vegvisirweb/nginx_server/default.conf:/etc/nginx/conf.d/default.conf:ro -p 8080:80 -d nginx \
		&>> '$(WORKING_DIRECTORY)/vegvisir_application_logs/docker.txt';\
		)
	@echo "Vegvisir now available at 127.0.0.1:8080"
	@( \
		echo 'Vegvisir: running backend';\
		source $(VENV)/bin/activate;\
		python ./vegvisirweb/__init__.py $(WORKING_DIRECTORY) $(PASSWORD) &>> '$(WORKING_DIRECTORY)/vegvisir_application_logs/QUART_backend.txt';\
	) 
	


web-dev: $(VENV)/bin/activate
	
	(  source $(VENV)/bin/activate;\
		cd vegvisirweb; npm i; npm run --silent dev | head -n 5;) &
	( \
		sleep 20;\
		source $(VENV)/bin/activate;\
		QUART_APP=vegvisirweb QUART_ENV=development quart run;\
	) 

run: $(VENV)/bin/activate
	$(PYTHON) vegvisir-cli/app.py

$(VENV)/bin/activate: requirements.txt
	@echo "Vegvisir: creating Python virtual environment and installing required packages (requirements.txt)";
	@python3 -m venv $(VENV) &>> '$(WORKING_DIRECTORY)/vegvisir_application_logs/docker.txt';
	@$(PIP) install -r requirements.txt &>> '$(WORKING_DIRECTORY)/vegvisir_application_logs/docker.txt';

clean:
	python3 -Bc "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
	python3 -Bc "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__')]"
	rm -rf $(VENV)
	rm -rf logs/*

# TODO: create client.env, shaper.env, server.env