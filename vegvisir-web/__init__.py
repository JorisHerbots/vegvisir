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
import threading 

app = Flask(__name__)


managerQueue = []
busy_manager = []

password = getpass.getpass("Please enter your sudo password: ")


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

	manager = Manager(password)
	request_form = request.json

	for client in request_form["clients"]:
		manager.add_active_implementation(client)

	for shaper in request_form["shapers"]:
		manager.add_active_implementation(shaper)

	for server in request_form["servers"]:
		manager.add_active_implementation(server)

	for testcase in request_form["testcases"]:
		print("added testcase")
		manager.add_active_testcase(testcase)

	print(manager._active_testcases)
	managerQueue.append(manager)

	return ""


@app.route("/GetQueue")
@cross_origin()
def GetQueue():
	pass




def runTestsThread():
	while True:
		if len(managerQueue) == 0:
			time.sleep(1)
		else:
			try:
				busy_manager = managerQueue.pop(0)
				print(managerQueue)
				busy_manager.run_tests()
				print("euuuhhhhh")
			except:
				pass


th = threading.Thread(target=runTestsThread)
th.start()



    
# @bp.route('/Implemenentations', methods=['GET'])
# def Implemenentations():


	
