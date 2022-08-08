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
import uuid
import traceback

from vegvisirweb.websocketqueue import WebSocketQueue, MessageSendWorker, MessageParser

app = Quart(__name__)



web_socket_queue = WebSocketQueue()
web_sockets_worker = MessageSendWorker()
web_socket_queue.add_worker(web_sockets_worker)


manager_queue = []
queue = []
busy_manager = None
last_status = ""
SocketWatcherEnabled = False
connected_sockets = set()

password = getpass.getpass("Please enter your sudo password: ")
loop = None

# Should correspond to tests.json file 
tests = {}
tests_updated = asyncio.Event()
test_connected_sockets = set()

with open("tests.json") as f:
	try:
		tests = json.load(f)
	except:
		tests = {}


def UpdateJSONfile():
	global tests 

	print("updating JSON file")

	json_string = json.dumps(tests)
	with open("tests.json", 'w') as outfile:
		outfile.write(json_string)

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
async def run_test():
	global tests
	global tests_updated

	id = str(uuid.uuid1())

	manager = Manager(password, id, add_message_to_queue_sync)
	
	request_form = await request.get_json()

	for client in request_form["configuration"]["clients"]:
		manager.add_active_implementation(client)

	for shaper in request_form["configuration"]["shapers"]:
		manager.add_active_implementation(shaper)

	for server in request_form["configuration"]["servers"]:
		manager.add_active_implementation(server)

	for testcase in request_form["configuration"]["testcases"]:
		print("added testcase")
		manager.add_active_testcase(testcase)


	dictionary = {}
	dictionary["id"] = id 
	dictionary["status"] = "waiting"
	dictionary["name"] = request_form["name"]
	dictionary["time_added"] = str(time.time())
	dictionary["configuration"] = request_form["configuration"]

	tests[id] = dictionary

	manager_queue.append(manager)
	
	await add_message_to_queue("add_test", json.dumps(dictionary))

	return ""


@app.route("/GetTests")
@route_cors()
async def GetTests():
	global tests

	return tests


# Consumer for websocket
# discards the data 
async def consumer():
	while True:
		data = await websocket.receive()


# Collects the web
#
def collect_testswebsocket(func):
	@wraps(func)
	async def wrapper(*args, **kwargs):
		global web_sockets_worker
		web_sockets_worker.add_websocket(websocket._get_current_object())
		print("added web socket to worker")
		try:
			return await func(*args, **kwargs)
		finally:
			web_sockets_worker.remove_websocket(websocket._get_current_object())
	return wrapper


# Websocket to send status updates about tests
@app.websocket('/TestsWebSocket')
@collect_testswebsocket
async def tests_websocket():
	consumer_task = asyncio.create_task(consumer())
	await websocket.accept()
	try:
		await asyncio.gather(consumer_task)
	finally:
		consumer_task.cancel()

# synchronous method to add a message to the web_socket_queue
# Use this version when you need to add something to the queue but you do not have acces to the event loop (eg. in another thread)
# params
#	message_type	: one of the available message types of the MessageParser class
# 	message			: the message to send
# post
#	Encoded version of message added to web_socket_queue
def add_message_to_queue_sync(message_type, message):
	global loop 
	asyncio.run_coroutine_threadsafe(add_message_to_queue(message_type, message), loop=loop)


# Asynchronous method to add a message to the web_socket_queue
# params
#	message_type	: one of the available message types of the MessageParser class
# 	message			: the message to send
# post
#	Encoded version of message added to web_socket_queue
async def add_message_to_queue(message_type, message):
	global web_socket_queue

	print(f"adding message to queue {message} with type {message_type}")
	try:
		encoded_message = MessageParser().encode_message(message_type, message)
	except Exception as e:
		print(e)
	await web_socket_queue.add_message(encoded_message)

def run_tests_thread():
	global busy_manager
	global tests
	global manager_queue
	global tests_updated 
	global loop

	while True:
		if len(manager_queue) == 0:
			busy_manager == None
			time.sleep(3)
		else:
			try:
				busy_manager = manager_queue.pop(0)
				
				tests[busy_manager._id]["status"] = "running"

				if loop != None:
					asyncio.run_coroutine_threadsafe(add_message_to_queue("update_test", json.dumps(tests[busy_manager._id])), loop=loop)
				busy_manager.run_tests()

				tests[busy_manager._id]["status"] = "done"

				if loop != None:
					asyncio.run_coroutine_threadsafe(add_message_to_queue("update_test", json.dumps(tests[busy_manager._id])), loop=loop)
			except Exception as e:
				print(e)
				print(traceback.format_exc())

@app.before_serving
async def lifespan():
	global loop
	loop = asyncio.get_event_loop()
	loop.create_task(web_socket_queue.watch_queue_and_notify_workers())


th = threading.Thread(target=run_tests_thread)
th.start()

