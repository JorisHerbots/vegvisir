from datetime import datetime
import logging
import subprocess
import threading
import time

from watchdog import observers
from watchdog.events import FileSystemEventHandler

from vegvisir.data import ExperimentPaths

class ABCSensor:
	def __init__(self) -> None:
		self.thread: threading.Thread = None
		self.terminate_sensor = False

	def setup(self, process_to_monitor: subprocess.Popen, actuator, sync_semaphore: threading.Thread, path_collection: ExperimentPaths):
		self.thread = threading.Thread(target=self.thread_target, args=(process_to_monitor, actuator, sync_semaphore,))
		self.terminate_sensor = False
		self.path_collection = path_collection

	def thread_target(self, client_process: subprocess.Popen, actuator, sync_semaphore: threading.Thread):
		"""
		Needs to be overwritten, no super() callback needed
		"""
		sync_semaphore.release()

class TimeoutSensor(ABCSensor):
	"""
	Timeout sensor
	Second precision
	"""
	
	def __init__(self, timeout: int) -> None:
		super().__init__()
		self.timeout_value = timeout

	def thread_target(self, client_process: subprocess.Popen, actuator, sync_semaphore: threading.Semaphore):
		sensor_start_time = datetime.now()
		while (datetime.now() - sensor_start_time).seconds < self.timeout_value and not self.terminate_sensor:
			if client_process is not None and client_process.poll() is not None:
				logging.info(f'TimeoutSensor detected client exit before timeout, halting timer. Ran for {(datetime.now() - sensor_start_time).seconds} seconds.')
				sync_semaphore.release()
				return
			time.sleep(1)

		if self.terminate_sensor:
			logging.info("TimeoutSensor stop requested")
			return
		sync_semaphore.release()
		logging.info('TimeoutSensor timeout triggered')
		if client_process is not None:
			client_process.terminate()
		if actuator is not None:
			actuator()

class FileWatchdogSensor(ABCSensor):
	pass