import threading
from typing import List
from zipfile import ZipFile
import tempfile

from werkzeug.utils import send_file
import time
from datetime import datetime
import os
import json

from vegvisir.manager import Manager

from flask import (
	Flask, Blueprint, render_template, request, flash, redirect, url_for, jsonify, abort
)
from flask_cors import cross_origin
import getpass

app = Flask(__name__)

password = getpass.getpass("Please enter your sudo password: ")
manager = Manager(password)

@app.route("/Implementations")
@cross_origin()
def Implemenentations():
    f = open("implementations.json")
    data = json.load(f)
    return data

@app.route("/Testcases")
@cross_origin()
def Testcases():
    f = open("testcases.json")
    data = json.load(f)
    return data

@app.route("/Runtest", methods=['POST'])
@cross_origin()
def Runtest():

	request_form = request.json
	print(request_form)

	print(request_form["clients"])


	for client in request_form["clients"]:
		manager.add_active_implementation(client)

	for shaper in request_form["shapers"]:
		manager.add_active_implementation(shaper)

	for server in request_form["servers"]:
		manager.add_active_implementation(server)

	for testcase in request_form["testcases"]:
		manager.add_active_testcase(testcase)

	manager.run_tests()

	return ""

    
# @bp.route('/Implemenentations', methods=['GET'])
# def Implemenentations():


	
