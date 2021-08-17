from datetime import datetime
from enum import Enum
import tempfile
import subprocess
import sys
import logging
from typing import List
from vegvisir.implementation import RunStatus, Scenario
import threading
import time
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

class Status(Enum):
	SUCCES = 1
	FAILED = 2

class Perspective(Enum):
	SERVER = "server"
	CLIENT = "client"
	SHAPER = "shaper"

class TestResult:
	start_time: datetime = 0
	end_time: datetime = 0
	status: Status = Status.FAILED

	def __init__(self):
		pass

class TestEnd:
	_thread: threading.Thread = None
	_process: subprocess.Popen = None

	def __init__(self):
		pass

	def setup(self, process):
		self._process = process

	#TODO give feedback to caller
	def wait_for_end(self):
		self._thread.start()
		self._thread.join()
		self._process.terminate()

class TestEndTimeout(TestEnd):
	_timeout: int = 0

	def __init__(self, timeout):
		super().__init__()
		self._timeout = timeout

	def setup(self, process):
		super().setup(process)

		def thread_func():
			ctime = datetime.now()
			#time.sleep(self._timeout)
			while (datetime.now()-ctime).seconds < self._timeout:
				if self._process.poll() != None:
					logging.info('client exited successfully')
					return
				time.sleep(1)
			logging.info('client timed out')
			
		self._thread = threading.Thread(target=thread_func)

class TestEndUntilDownload(TestEnd):
	_timeout: int = 0

	def __init__(self, timeout):
		super().__init__()
		self._timeout = timeout

	def setup(self, process, path, file):
		super().setup(process)
		global running
		running = True

		class DownloadHandler(FileSystemEventHandler):
			def on_created(self, event):
				#logging.debug(f'event type: {event.event_type}  path : {event.src_path}')
				if event.src_path == path + '/' + file:
					global running
					running = False
					#print('found %s!', file)

		def thread_func():
			event_handler = DownloadHandler()
			observer = Observer()
			observer.schedule(event_handler, path) #TODO set path to check
			observer.start()
			client_exited = False

			ctime = datetime.now()
			global running
			while running and ((datetime.now()-ctime).seconds < self._timeout):
				if not client_exited and self._process.poll() != None:
					logging.info('client exited before download')
					client_exited = True
					observer.stop()
					return
				time.sleep(1)
			observer.stop()
			logging.info('client timed out')
		
		self._thread = threading.Thread(target=thread_func)


class TestCase:
	name: str = ""

	origin: str = "server4:443"
	request_urls: str = "https://server4:443"

	_www_dir = None
	_download_dir = None
	_cert_dir = None

	cert_fingerprint: str = ""
	
	scenario: Scenario = None
	testend: TestEnd = TestEndTimeout(60)

	def __init__(self):
		pass

	def www_dir(self):
		if not self._www_dir:
			self._www_dir = tempfile.TemporaryDirectory(dir="/tmp", prefix="www_")
		return self._www_dir.name + "/"

	def download_dir(self):
		if not self._download_dir:
			self._download_dir = tempfile.TemporaryDirectory(
				dir="/tmp", prefix="download_"
			)
		return self._download_dir.name + "/"

	def certs_dir(self):
		if not self._cert_dir:
			self._cert_dir = tempfile.TemporaryDirectory(dir="/tmp", prefix="certs_")
			self.cert_fingerprint = generate_cert_chain(self._cert_dir.name)
		return self._cert_dir.name + "/"

	def testname(self, perspective: Perspective):
		return self.name

	def additional_containers(self) -> List[str]:
		return [""]

	def additional_envs(self) -> List[str]:
		return [""]

class ServeTest(TestCase):

	def __init__(self):
		super().__init__()
		self.name = "servetest"
		self.testend = TestEndUntilDownload(300)

		self._www_dir = StaticDirectory("./www")
		self.request_urls: str = "https://server4:443/dashjs-qlog-abr/demo/demo.html?testrun"

	def testname(self, perspective: Perspective):
		if perspective == Perspective.SERVER:
			return "http3"
		return super().testname(perspective)

	def additional_containers(self) -> List[str]:
		return []#["iperf_server", "iperf_client"]

	def additional_envs(self) -> List[str]:
		return ["IPERF_CONGESTION=cubic"]

def generate_cert_chain(directory: str, length: int = 1):
	cmd = "./certs.sh " + directory + " " + str(length)
	r = subprocess.run(
		cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
	)
	logging.debug("%s", r.stdout.decode("utf-8"))
	if r.returncode != 0:
		logging.info("Unable to create certificates")
		sys.exit(1)
	cmd = "./certs-fingerprint.sh " + directory
	r = subprocess.run(
		cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
	)
	fingerprint = r.stdout.decode("utf-8").strip()
	logging.debug("certificate fingerprint: %s", fingerprint)
	return fingerprint

class StaticDirectory():
	name: str = ""

	def __init__(self, name):
		self.name = name

class TestCaseWrapper():
	testcase = None
	active: bool = False
	status: RunStatus = RunStatus.WAITING

## List of all supported tests
TESTCASES = [
	ServeTest
]