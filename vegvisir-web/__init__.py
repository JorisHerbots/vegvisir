import threading
from typing import List
from zipfile import ZipFile
import tempfile

from functools import wraps
from werkzeug.utils import send_file
import time
from datetime import datetime
import os
import json

from vegvisir.manager import Manager

from quart import Quart,websocket,request

from quart_cors import route_cors
import getpass
import threading 
import asyncio

app = Quart(__name__)

manager_queue = []
queue = []
busy_manager = None
last_status = ""
SocketWatcherEnabled = False
connected_sockets = set()

password = getpass.getpass("Please enter your sudo password: ")




@app.route("/Implementations")
@route_cors()
async def Implemenentations():
    f = open("implementations.json")
    data = json.load(f)
    return data

@app.route("/Testcases")
@route_cors()
async def Testcases():
    f = open("testcases.json")
    data = json.load(f)
    return data

@app.route("/Runtest", methods=['POST'])
@route_cors()
async def Runtest():
	global queue 
	manager = Manager(password, queue)
	request_form = await request.get_json()

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
	manager_queue.append(manager)

	return ""

async def consumer():
	while True:
		data = await websocket.receive()


def collect_websocket(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        global connected_sockets
        connected_sockets.add(websocket._get_current_object())
        try:
            return await func(*args, **kwargs)
        finally:
            connected_sockets.remove(websocket._get_current_object())
    return wrapper


@app.websocket('/ws')
@collect_websocket
async def ws():
	global last_status

	consumer_task = asyncio.create_task(consumer())
	await websocket.send(last_status)
	try:
		await asyncio.gather(consumer_task)
	finally:
		consumer_task.cancel()

async def SocketWatcher():
	global queue
	global connected_sockets
	global last_status
	while True: 
		if len(queue) == 0:
			await asyncio.sleep(1)
		else:
			try:
				message = queue.pop(0)
				last_status = message
	
				for ws in connected_sockets:
					try:
						await ws.send(message)
					except:
						pass			
			except:		
				pass



def runTestsThread():
	global busy_manager
	while True:
		if len(manager_queue) == 0:
			busy_manager == None
			time.sleep(3)
		else:
			try:
				busy_manager = manager_queue.pop(0)
				print(manager_queue)
				busy_manager.run_tests()
			except:
				pass

@app.before_serving
async def lifespan():
	loop = asyncio.get_event_loop()
	loop.create_task(SocketWatcher())


th = threading.Thread(target=runTestsThread)
th.start()
