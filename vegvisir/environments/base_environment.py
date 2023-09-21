import logging
import subprocess
import threading
from ast import List
from enum import Enum
from typing import Tuple

from vegvisir.data import ExperimentPaths
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
		self.environment_name:str = ""
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

	def start_sensors(self, process_to_monitor = None, path_collection: ExperimentPaths = ExperimentPaths()) -> None:
		if len(self.sensors) == 0:
			raise VegvisirEnvironmentException("Environment sensorlist empty. Can't comply with start request.")

		# Python can enter a racecondition when interrupts happens during a Thread.join()
		# https://github.com/python/cpython/issues/90882
		# Since we allow users to use Ctrl+C keyboard interrupts to shortcut a test/run, this would trigger this bug
		# Instead of relying on Thread.join(), we work around it by using a semaphore.
		# Any sensor can trigger a .release() which would indicate a sensor has triggered
		self.sync_semaphore = threading.Semaphore(0)

		for sensor in self.sensors:
			sensor.setup(process_to_monitor, self.forcestop_sensors, self.sync_semaphore, path_collection)
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


	def pre_run_hook(self, paths: ExperimentPaths):
		"""
		Called right after initial setup is completed (i.e., logging directories, ...) and before client, shaper and server are spun up
		"""
		pass

	def post_run_hook(self, paths: ExperimentPaths):
		"""
		Called after run has completed and everything is cleaned up
		"""
		pass
