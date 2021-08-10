import os

from flask import Flask

def create_app(test_config=None):
	# create and configure the app
	myapp = Flask(__name__, instance_relative_config=True)
	myapp.config.from_mapping(
		SECRET_KEY='dev',
	)

	if test_config is None:
		# load the instance config, if it exists, when not testing
		myapp.config.from_pyfile('config.py', silent=True)
	else:
		# load the test config if passed in
		myapp.config.from_mapping(test_config)

	from . import app
	myapp.register_blueprint(app.bp)

	return myapp