from datetime import datetime
import logging
import subprocess
import threading
import time


class ABCSensor:
	def __init__(self) -> None:
		self.thread: threading.Thread = None
		self.terminate_sensor = False

	def setup(self, client_process: subprocess.Popen, actuator, sync_semaphore: threading.Thread):
		self.thread = threading.Thread(target=self.thread_target, args=(client_process, actuator, sync_semaphore,))
		self.terminate_sensor = False

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
				logging.info('TimeoutSensor detected client exit before timeout, halting timer.')
				sync_semaphore.release()
				return
			print(self.terminate_sensor)
			time.sleep(1)

		print("Fuck")
		if self.terminate_sensor:
			logging.info("TimeoutSensor stop request handled")
			return
		sync_semaphore.release()
		logging.info('TimeoutSensor timeout triggered')
		if actuator is not None:
			actuator()

class FileWatchdogSensor(ABCSensor):
	pass