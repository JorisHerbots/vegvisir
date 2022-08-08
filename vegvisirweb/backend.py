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

app = Flask(__name__)

manager = Manager("olaf")

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


    return "lol"





# @bp.route('/Implemenentations', methods=['GET'])
# def Implemenentations():


	
