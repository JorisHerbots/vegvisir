import threading
from typing import List
from zipfile import ZipFile
import tempfile

from functools import wraps
# from werkzeug.utils import send_file
import time
from datetime import datetime
import os
import sys 
import json

from vegvisir.manager import Manager

from quart import Quart,websocket,request,send_file

from quart_cors import route_cors
import getpass
import threading 
import asyncio
import uuid
import traceback

import sqlite3 

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


sqlite_connection = sqlite3.connect("vegvisir.db")
sqlite_cursor = sqlite_connection.cursor()

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
	global sqlite_cursor
	global sqlite_connection

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
	manager.name = request_form["name"]

	dictionary["time_added"] = str(time.time())
	dictionary["configuration"] = request_form["configuration"]


	tests[id] = dictionary

	manager_queue.append(manager)
	
	sqlite_cursor.execute('INSERT INTO tests VALUES(?,?,?,?,?)', (id, dictionary["name"], json.dumps(dictionary), "waiting", False))
	sqlite_connection.commit()

	await add_message_to_queue("add_test", json.dumps(dictionary))

	return ""


@app.route("/GetTests")
@route_cors()
async def GetTests():
	#global tests

	tests = {}

	for row in sqlite_cursor.execute("SELECT json FROM tests WHERE removed != 1"):
		tests[json.loads(row[0])["id"]] = (json.loads(row[0]))

	return tests


# Consumer for websocket
# discards the data 
async def consumer():
	global tests

	while True:
		data = await websocket.receive()

		(message_type, message) = MessageParser().decode_message(data)

		if (message_type == "request_all_logfiles"):
			filenames = []
			
			try:
				test = tests[message]
				for log_dir in test["log_dirs"]:
					filenames.extend(await get_filenames_from_folder(log_dir))
			except Exception as e:
				print(e)
				print(traceback.format_exc())

			await add_message_to_queue("update_all_logfiles", json.dumps(filenames))

		if (message_type == "request_logfiles_in_folder"):
			filenames = []
			log_dir = message
			
			try:
				filenames.extend(await get_filenames_from_folder(log_dir))
			except Exception as e:
				print(e)
				print(traceback.format_exc())

			await add_message_to_queue("update_all_logfiles", json.dumps(filenames))


		if (message_type == "remove_test"):

			sqlite_cursor.execute("UPDATE tests SET removed = 1 WHERE id = :id", {"id": message}) 
			sqlite_connection.commit()

	

# Collects the web
#
def collect_testswebsocket(func):
	@wraps(func)
	async def wrapper(*args, **kwargs):
		global web_sockets_worker
		web_sockets_worker.add_websocket(websocket._get_current_object())
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

@app.route('/logs/<path:req_path>')
@route_cors()
async def log_listing(req_path):
	BASE_DIR = os.getcwd() + '/logs'

	# Joining the base and the requested path
	abs_path = os.path.join(BASE_DIR, req_path)

	# print(BASE_DIR)
	# print(req_path)
	# print(abs_path)

	# Return 404 if path doesn't exist
	if not os.path.exists(abs_path):
		return abort(404)

	# Check if path is a file and serve
	if os.path.isfile(abs_path):
		return await send_file(abs_path, as_attachment=True)

	# Show directory contents
	files = os.listdir(abs_path)
	return files


def run_tests_thread():
	global busy_manager
	global tests
	global manager_queue
	global tests_updated 
	global loop

	sqlite_connection_worker_thread = sqlite3.connect("vegvisir.db")
	sqlite_cursor_worker_thread = sqlite_connection_worker_thread.cursor()

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

				sqlite_cursor_worker_thread.execute('UPDATE tests SET status = "running", json = :json WHERE id = :id', {"id": busy_manager._id, "json": json.dumps(tests[busy_manager._id])})
				sqlite_connection_worker_thread.commit()

				log_dirs = busy_manager.run_tests()

				tests[busy_manager._id]["status"] = "done"
				tests[busy_manager._id]["log_dirs"] = log_dirs

				if loop != None:
					asyncio.run_coroutine_threadsafe(add_message_to_queue("update_test", json.dumps(tests[busy_manager._id])), loop=loop)

				sqlite_cursor_worker_thread.execute('UPDATE tests SET status = "done", json= :json WHERE id = :id', {"id": busy_manager._id, "json": json.dumps(tests[busy_manager._id])})
				sqlite_connection_worker_thread.commit()
				
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



async def get_filenames_from_folder(root):
	# TODO: make finding directory cleaner
	#cwd = os.getcwd() + "/logs"

	#root = cwd + root

	file_list = []


	for path, subdirs, files in os.walk(root):
		for name in files:
			file_list.append(os.path.join(path, name))

	return file_list


# Gets filenames from this folder and subfolders
@app.route('/FilesInPath')
@route_cors()
async def get_filenames_from_folder_req():
	# TODO: make finding directory cleaner
	cwd = os.getcwd() + "/logs"

	root = cwd + request.args.get("path")

	file_list = []


	for path, subdirs, files in os.walk(root):
		for name in files:
			file_list.append(os.path.join(path, name))

	return file_list