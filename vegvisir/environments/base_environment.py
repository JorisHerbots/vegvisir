from ast import List
from datetime import datetime
from enum import Enum
import logging
import subprocess
import threading
import time
from typing import Tuple
from vegvisir.environments import sensors

class VegvisirEnvironmentException(Exception):
	pass



class BaseEnvironment:
	"""
	(Abstract) base class for runner environments
	Should not be used as environment directly, but rather as class to extend upon (but don't let me be the person to stop you :) )
	"""

	class Perspective(Enum):
		CLIENT = "client"
		SERVER = "server"
		

	def __init__(self) -> None:
		self._QIR_compatibility_testcase_client:str = ""  # Undefined QIR behavior
		self._QIR_compatibility_testcase_server:str = ""  # Undefined QIR behavior
		self.scenario:str = ""
		self.sensors:List[sensors.ABCSensor] = []
		self.sync_semaphore = None

	def get_QIR_compatibility_testcase(self, perspective: Perspective) -> str:
		if perspective == BaseEnvironment.Perspective.CLIENT:
			return self._QIR_compatibility_testcase_client
		elif perspective == BaseEnvironment.Perspective.SERVER:
			return self._QIR_compatibility_testcase_server
		return None

	def set_QIR_compatibility_testcase(self, testcase: str | Tuple[str, Perspective]) -> None:
		testcase, perspective = testcase if type(testcase) is tuple else (testcase, None)		
		if perspective == BaseEnvironment.Perspective.CLIENT:
			self._QIR_compatibility_testcase_client = testcase
		elif perspective == BaseEnvironment.Perspective.SERVER:
			self._QIR_compatibility_testcase_client = testcase
		else:
			self._QIR_compatibility_testcase_client = testcase
			self._QIR_compatibility_testcase_server = testcase

	def generate_cert_chain(self, directory: str, length: int = 1):
		cmd = "./certs.sh " + directory + " " + str(length)
		r = subprocess.run(
			cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
		)
		logging.debug("Vegvisir: %s", r.stdout.decode("utf-8"))
		if r.returncode != 0:
			raise VegvisirEnvironmentException("Unable to create certificates")
		cmd = "./certs-fingerprint.sh " + directory
		r = subprocess.run(
			cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
		)
		fingerprint = r.stdout.decode("utf-8").strip()
		logging.debug("Vegvisir: certificate fingerprint: %s", fingerprint)
		return fingerprint

	def add_sensor(self, sensor: sensors.ABCSensor) -> None:
		sensor.sensor_actuator = self.forcestop_sensors
		self.sensors.append(sensor)

	def start_sensors(self, process_to_monitor = None) -> None:
		if len(self.sensors) == 0:
			raise VegvisirEnvironmentException("Environment sensorlist empty. Can't comply with start request.")

		# Python can enter a racecondition when interrupts happens during a Thread.join()
		# https://github.com/python/cpython/issues/90882
		# Since we allow users to use Ctrl+C keyboardinterrupts to shortcut a test/run, this would trigger this bug
		# Instead of relying on Thread.join(), we work around it by using a semaphore.
		# Any sensor can trigger a .release() which would indicate a sensor has triggered
		self.sync_semaphore = threading.Semaphore(0)

		for sensor in self.sensors:
			sensor.setup(process_to_monitor , self.forcestop_sensors, self.sync_semaphore)
			sensor.thread.start()

	def forcestop_sensors(self) -> None:
		for sensor in self.sensors:
			sensor.terminate_sensor = True

	def waitfor_sensors(self) -> None:
		self.sync_semaphore.acquire()
		
	def clean_and_reset_sensors(self) -> None:
		for sensor in self.sensors:
			if sensor.thread.is_alive():
				sensor.thread.join()
			sensor.terminate_sensor = True


	def pre_run_hook(self):  # TODO jherbots pass through paths
		"""
		Called right after initial setup is completed (i.e., logging directories, ...) and before client, shaper and server are spun up
		"""
		pass

	def post_run_hook(self):  # TODO jherbots pass through paths
		"""
		Called after run has completed and everything is cleaned up
		"""
		pass




# from datetime import datetime
# from enum import Enum
# import tempfile
# import subprocess
# import sys
# import logging
# from typing import List
# from vegvisir.implementation import RunStatus, Scenario
# import threading
# import time
# from watchdog.events import FileSystemEventHandler
# from watchdog.observers import Observer

# class Status(Enum):
# 	SUCCES = 1
# 	FAILED = 2

# class Perspective(Enum):
# 	SERVER = "server"
# 	CLIENT = "client"
# 	SHAPER = "shaper"

# class TestResult:
# 	start_time: datetime = 0
# 	end_time: datetime = 0
# 	status: Status = Status.FAILED

# 	def __init__(self):
# 		pass

# class TestEnd:
# 	_thread: threading.Thread = None
# 	_process: subprocess.Popen = None

# 	def __init__(self):
# 		pass

# 	def setup(self, process):
# 		self._process = process

# 	#TODO give feedback to caller
# 	def wait_for_end(self):
# 		self._thread.start()
# 		self._thread.join()
# 		self._process.terminate()

# class TestEndTimeout(TestEnd):
# 	_timeout: int = 0

# 	def __init__(self):
# 		super().__init__()

# 	def setup(self, process, timeout):
# 		super().setup(process)
# 		self._timeout = timeout

# 		def thread_func():
# 			ctime = datetime.now()
# 			#time.sleep(self._timeout)
# 			while (datetime.now()-ctime).seconds < self._timeout:
# 				if self._process.poll() != None:
# 					logging.info('client exited successfully')
# 					return
# 				time.sleep(1)
# 			logging.info('client timed out')
			
# 		self._thread = threading.Thread(target=thread_func)

# class TestEndUntilDownload(TestEnd):
# 	_timeout: int = 0

# 	def __init__(self):
# 		super().__init__()

# 	def setup(self, process, path, file, timeout):
# 		super().setup(process)
# 		global running
# 		running = True
# 		self._timeout = timeout

# 		class DownloadHandler(FileSystemEventHandler):
# 			def on_created(self, event):
# 				#logging.debug(f'event type: {event.event_type}  path : {event.src_path}')
# 				if event.src_path == path + '/' + file:
# 					global running
# 					running = False
# 					#print('found %s!', file)

# 		def thread_func():
# 			event_handler = DownloadHandler()
# 			observer = Observer()
# 			observer.schedule(event_handler, path) #TODO set path to check
# 			observer.start()
# 			client_exited = False

# 			ctime = datetime.now()
# 			global running
# 			while running and ((datetime.now()-ctime).seconds < self._timeout):
# 				if not client_exited and self._process.poll() != None:
# 					logging.info('client exited before download')
# 					client_exited = True
# 					observer.stop()
# 					return
# 				time.sleep(1)
# 			observer.stop()
# 			logging.info('client timed out')
		
# 		self._thread = threading.Thread(target=thread_func)


# class TestCase:
# 	name: str = ""

# 	origin: str = "server4:443"
# 	request_urls: str = "https://server4:443"

# 	_www_dir = None
# 	_download_dir = None
# 	_cert_dir = None

# 	cert_fingerprint: str = ""
	
# 	scenario: Scenario = None
# 	testend: TestEnd = TestEndTimeout()

# 	def __init__(self):
# 		pass

# 	def www_dir(self):
# 		if not self._www_dir:
# 			self._www_dir = tempfile.TemporaryDirectory(dir="/tmp", prefix="www_")
# 		return self._www_dir.name + "/"

# 	def download_dir(self):
# 		if not self._download_dir:
# 			self._download_dir = tempfile.TemporaryDirectory(
# 				dir="/tmp", prefix="download_"
# 			)
# 		return self._download_dir.name + "/"

# 	def certs_dir(self):
# 		if not self._cert_dir:
# 			self._cert_dir = tempfile.TemporaryDirectory(dir="/tmp", prefix="certs_")
# 			self.cert_fingerprint = generate_cert_chain(self._cert_dir.name)
# 		return self._cert_dir.name + "/"

# 	def testname(self, perspective: Perspective):
# 		return self.name

# 	def additional_containers(self) -> List[str]:
# 		return [""]

# 	def additional_envs(self) -> List[str]:
# 		return [""]

# class ServeTest(TestCase):
# 	file_to_find = "create-name-todo.json"
# 	timeout_time = 60

# 	def __init__(self):
# 		super().__init__()
# 		self.name = "servetest"
# 		self.testend = TestEndUntilDownload()

# 		self._www_dir = StaticDirectory("./www")
# 		self.request_urls: str = "https://server4:443/video/bbb/BigBuckBunny_1s_simple_2014_05_09.mpd"

# 	def testname(self, perspective: Perspective):
# 		if perspective == Perspective.SERVER:
# 			return "http3"
# 		return super().testname(perspective)

# 	def additional_containers(self) -> List[str]:
# 		return []#["iperf_server", "iperf_client"]

# 	def additional_envs(self) -> List[str]:
# 		return ["IPERF_CONGESTION=cubic"]

# def generate_cert_chain(directory: str, length: int = 1):
# 	cmd = "./certs.sh " + directory + " " + str(length)
# 	r = subprocess.run(
# 		cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
# 	)
# 	logging.debug("Vegvisir: %s", r.stdout.decode("utf-8"))
# 	if r.returncode != 0:
# 		logging.info("Unable to create certificates")
# 		sys.exit(1)
# 	cmd = "./certs-fingerprint.sh " + directory
# 	r = subprocess.run(
# 		cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
# 	)
# 	fingerprint = r.stdout.decode("utf-8").strip()
# 	logging.debug("Vegvisir: certificate fingerprint: %s", fingerprint)
# 	return fingerprint

# class StaticDirectory():
# 	name: str = ""

# 	def __init__(self, name):
# 		self.name = name

# class TestCaseWrapper():
# 	testcase = None
# 	active: bool = False
# 	status: RunStatus = RunStatus.WAITING

# ## List of all supported tests
# TESTCASES = [
# 	ServeTest
# ]