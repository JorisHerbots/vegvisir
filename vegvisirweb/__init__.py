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
from vegvisir.docker_manager import *

from vegvisirweb.websocketqueue import WebSocketQueue, MessageSendWorker, MessageParser

app = Quart(__name__)

IMAGESETS_IMPORT_EXPORT_DIRECTORY = "./imagesets_import_export"
IMPLEMENTATIONS_JSON = "implementations.json"
TESTCASES_JSON = "testcases.json"

web_socket_queue = WebSocketQueue()
web_sockets_worker = MessageSendWorker()
web_socket_queue.add_worker(web_sockets_worker)

manager_queue = []
queue = []
busy_manager = None
running_test_last_status = ""
SocketWatcherEnabled = False
connected_sockets = set()

password = getpass.getpass("Please enter your sudo password: ")
loop = None


sqlite_connection = sqlite3.connect("vegvisir.db")
sqlite_cursor = sqlite_connection.cursor()


tests = {}

with open("tests.json") as f:
	try:
		tests = json.load(f)
	except:
		tests = {}

# Returns all implementation in the general implementations json file and all the
# implementation from the loaded imagesets from their respective json file
# returns:
#	dictionary with as key the name of the implementation and as value another dictionary with all the information/parameters
def getAllImplementations():
	f = open(IMPLEMENTATIONS_JSON)
	data = json.load(f)

	all_implementations_json = data
    
	imageset_json_paths = glob.glob(os.path.join("./implementations", "*.json"))
	
	for imageset_json_path in imageset_json_paths:

		filename = imageset_json_path.split("/")[-1]
		imageset_name = filename.replace(".json", "")


		f = open(imageset_json_path)
		imageset_json = json.load(f)

		if imageset_json["enabled"]:
			for value in imageset_json["implementations"]:
				data = imageset_json["implementations"][value]
				all_implementations_json[imageset_name + "/" + value] = data
	
	return all_implementations_json

# Returns all the testcases
# returns:
#	dictionary with as key the name of the testcase and as value another dictionary with the information/parameters
def getAllTestcases():
    f = open(TESTCASES_JSON)
    data = json.load(f)
    return data

# Route to run a test
@app.route("/Runtest", methods=['POST'])
@route_cors()
async def run_test():
	global tests
	global sqlite_cursor
	global sqlite_connection

	id = str(uuid.uuid1())

	manager = Manager(password, id, manager_add_to_test_queue_callback)
	
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

	await add_message_to_queue(web_socket_queue, "add_test", json.dumps(dictionary))

	return ""


def manager_add_to_test_queue_callback(message_type, message):
	add_message_to_queue_sync(web_socket_queue, message_type, message)

# Route to get tests 
@app.route("/GetTests")
@route_cors()
async def GetTests():
	tests = {}

	for row in sqlite_cursor.execute("SELECT json FROM tests WHERE removed != 1"):
		tests[json.loads(row[0])["id"]] = (json.loads(row[0]))

	return tests

# returns: 
#	dictionary with as keys the names of the loaded imagesets and as values the string "true" or "false" representing if the imageset is enabled or not
def imagesets_get_loaded():
	loaded_imagesets = set()

	proc = subprocess.run(
		"docker images | awk '{print $1, $2}'",
		shell=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT
	)
	local_images = proc.stdout.decode('utf-8').replace(' ', ':').split('\n')[1:]
	
	for img in local_images:
		repo = get_repo_from_image(img)
		if repo == "vegvisir":
			set_name = get_name_from_image(img)
			loaded_imagesets.add(set_name)

	combined_list = {}
	imageset_json_paths = glob.glob(os.path.join("./implementations", "*.json"))

	for imageset_json_path in imageset_json_paths:

		filename = imageset_json_path.split("/")[-1]
		imageset_name = filename.replace(".json", "")	

		if imageset_name in loaded_imagesets:

			f = open(imageset_json_path)
			imageset_json = json.load(f)

			combined_list[imageset_name] = imageset_json["enabled"]

	return combined_list

# Gets the image names from docker
# returns:
#	list with strings representing the names of the loaded images
def imageset_get_images(imageset_name):
	images = set()

	proc = subprocess.run(
		"docker images | awk '{print $1, $2}'",
		shell=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT
	)
	local_images = proc.stdout.decode('utf-8').replace(' ', ':').split('\n')[1:]
	
	for img in local_images:
		repo = get_repo_from_image(img)
		if repo == "vegvisir":
			set_name = get_name_from_image(img)
			if set_name == imageset_name:
				images.add(set_name)
			
	return list(images)


# Consumer for imagesets websocket
# discards the data 
async def websocket_consumer():
	global tests

	while True:
		data = await websocket.receive()

		(message_type, message) = MessageParser().decode_message(data)

		if (message_type == "request_all_logfiles"):
			filenames = []
			
			try:
				# grab the json in string format
				test = sqlite_cursor.execute("SELECT json FROM tests WHERE id = :id", {"id": message}).fetchone()[0]
				
				# convert to python dictionary
				test =  json.loads(test)

				for log_dir in test["log_dirs"]:
					filenames.extend(await get_filepaths_from_directory(log_dir))
			except Exception as e:
				print(e)
				print(traceback.format_exc())

			await add_message_to_queue(web_socket_queue, "update_all_logfiles", json.dumps(filenames))

		if (message_type == "request_logfiles_in_folder"):
			filenames = []
			log_dir = message
			
			try:
				filenames.extend(await get_filepaths_from_directory(log_dir))
			except Exception as e:
				print(e)
				print(traceback.format_exc())

			await add_message_to_queue(web_socket_queue, "update_all_logfiles", json.dumps(filenames))


		if (message_type == "remove_test"):

			sqlite_cursor.execute("UPDATE tests SET removed = 1 WHERE id = :id", {"id": message}) 
			sqlite_connection.commit()

		if (message_type == "request_status_update"):
			global running_test_last_status
			
			await add_message_to_queue(web_socket_queue, "progress_update", running_test_last_status)

		if message_type == "imagesets_request_available":
			filenames = await get_filenames_from_directory(IMAGESETS_IMPORT_EXPORT_DIRECTORY)

			await add_message_to_queue(web_socket_queue, "imagesets_update_available", json.dumps(filenames))

		if message_type == "imagesets_request_loaded":
			#TODO: also check json ?
			loaded_imagesets = imagesets_get_loaded()

			await add_message_to_queue(web_socket_queue, "imagesets_update_loaded", json.dumps(loaded_imagesets))

		if message_type == "imagesets_request_images":
			#TODO: also check json ?

			images = imageset_get_images(message)

			net_images = {}
			net_images["name"] = message 
			net_images["images"] = images

			await add_message_to_queue(web_socket_queue, "imagesets_update_images", json.dumps(net_images))

		if message_type == "imagesets_load_imageset":
			
			# Import imageset
			zip_file_name = message 
			zip_file_path = os.path.join(IMAGESETS_IMPORT_EXPORT_DIRECTORY, zip_file_name)

			docker_import_imageset(zip_file_path)

			# Send update of loaded imagesets
			loaded_imagesets = imagesets_get_loaded()
			await add_message_to_queue(web_socket_queue, "imagesets_update_loaded", json.dumps(loaded_imagesets))

		if message_type == "imagesets_remove_imageset":
			
			docker_remove_imageset(message)
			
			# Send update of loaded imagesets
			loaded_imagesets = imagesets_get_loaded()
			await add_message_to_queue(web_socket_queue, "imagesets_update_loaded", json.dumps(loaded_imagesets))
			
		if message_type == "imagesets_activate_imageset":
			print("request to activate " + message)

			setname = message 
			output_file_url = os.path.join("./implementations/", setname.replace("/", "_") + ".json")
			imageset_json = {}

			with open(output_file_url) as input_file:
				imageset_json = json.load(input_file)

			imageset_json["enabled"] = True

			with open(output_file_url, 'w') as output_file:
				output_file.write(json.dumps(imageset_json))


		if message_type == "imagesets_disable_imageset":
			print("request to disable " + message)
			
			setname = message 
			output_file_url = os.path.join("./implementations/", setname.replace("/", "_") + ".json")
			imageset_json = {}

			with open(output_file_url) as input_file:
				imageset_json = json.load(input_file)

			imageset_json["enabled"] = False

			with open(output_file_url, 'w') as output_file:
				output_file.write(json.dumps(imageset_json))


		if message_type == "imageset_request_create":
			setname = message 
			f = open("implementations.json")
			data = json.load(f)

			docker_create_imageset(data, setname)

			#TODO: also check json ?
			loaded_imagesets = imagesets_get_loaded()

			await add_message_to_queue(web_socket_queue, "imagesets_update_loaded", json.dumps(loaded_imagesets))


		if message_type == "imageset_request_export":
			setname = message
			docker_export_imageset(setname)
			
			# Send update of available imagesets
			filenames = await get_filenames_from_directory(IMAGESETS_IMPORT_EXPORT_DIRECTORY)

			await add_message_to_queue(web_socket_queue, "imagesets_update_available", json.dumps(filenames))


		if message_type == "implementations_request":
			all_implementations = getAllImplementations()

			await add_message_to_queue(web_socket_queue, "implementations_update", json.dumps(all_implementations))

		if message_type == "implementations_testcases_request":
			all_testcases = getAllTestcases()

			await add_message_to_queue(web_socket_queue, "implementations_testcases_update", json.dumps(all_testcases))


		# "implementations_request": "IMR",
        # "implementations_update": "IMU",
        # "implementations_testcases_request": "ITR",
        # "implementations_testcases_update": "ITU"


def collect_websockets(func):
	@wraps(func)
	async def wrapper(*args, **kwargs):
		global web_sockets_worker
		web_sockets_worker.add_websocket(websocket._get_current_object())
		try:
			return await func(*args, **kwargs)
		finally:
			web_sockets_worker.remove_websocket(websocket._get_current_object())
	return wrapper

@app.websocket("/WebSocket")
@collect_websockets
async def imagesets_websocket():
	consumer_task = asyncio.create_task(websocket_consumer())
	await websocket.accept()
	try:
		await asyncio.gather(consumer_task)
	finally:
		consumer_task.cancel()

# synchronous method to add a message to the provided queue
# Use this version when you need to add something to the queue but you do not have acces to the event loop (eg. in another thread)
# params
#	message_type	: one of the available message types of the MessageParser class
# 	message			: the message to send
# post
#	Encoded version of message added to provided queue
def add_message_to_queue_sync(queue, message_type, message):
	global loop 
	asyncio.run_coroutine_threadsafe(add_message_to_queue(queue, message_type, message), loop=loop)

# Asynchronous method to add a message to the provided queu
# params
#	message_type	: one of the available message types of the MessageParser class
# 	message			: the message to send
# post
#	Encoded version of message added to the provided queue
async def add_message_to_queue(queue, message_type, message):
	global running_test_last_status

	print(f"adding message to queue {message} with type {message_type}")
	try:

		# Keep track of the last test progress update
		if message_type == "progress_update":
			running_test_last_status = message 

		encoded_message = MessageParser().encode_message(message_type, message)
	except Exception as e:
		print(e)
	await queue.add_message(encoded_message)

# Route to get logs
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
					asyncio.run_coroutine_threadsafe(add_message_to_queue(web_socket_queue, "update_test", json.dumps(tests[busy_manager._id])), loop=loop)

				sqlite_cursor_worker_thread.execute('UPDATE tests SET status = "running", json = :json WHERE id = :id', {"id": busy_manager._id, "json": json.dumps(tests[busy_manager._id])})
				sqlite_connection_worker_thread.commit()

				log_dirs = busy_manager.run_tests()

				tests[busy_manager._id]["status"] = "done"
				tests[busy_manager._id]["log_dirs"] = log_dirs

				if loop != None:
					asyncio.run_coroutine_threadsafe(add_message_to_queue(web_socket_queue, "update_test", json.dumps(tests[busy_manager._id])), loop=loop)

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
	loop.create_task(web_socket_queue.watch_queue_and_notify_workers())


th = threading.Thread(target=run_tests_thread)
th.start()

# returns all the filenames in the provided directory
# param:
#	root: directory path with or without trailing /
# returns:
#  list with filenames in directory				
async def get_filenames_from_directory(root):

	filepath_list = await get_filepaths_from_directory(root)
	file_list = []


	for path in filepath_list:
		file_list.append(path.split("/")[-1])

	return file_list

# returns all the filepaths in the provided directory
# param:
#	root: directory path with or without trailing /
# returns:
#  list with filepaths of files in directory			
async def get_filepaths_from_directory(root):
	file_list = []


	for path, subdirs, files in os.walk(root):
		for name in files:
			file_list.append(os.path.join(path, name))

	return file_list

