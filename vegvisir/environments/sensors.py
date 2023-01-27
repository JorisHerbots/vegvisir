from datetime import datetime
import logging
import subprocess
import threading
import time
from typing import List

import pyinotify

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
		logging.info(f'TimeoutSensor timeout triggered [{self.timeout_value}sec]')
		if client_process is not None:
			client_process.terminate()
		if actuator is not None:
			actuator()

class BrowserDownloadWatchdogSensor(ABCSensor):
	def __init__(self, expected_filename: str|List[str]) -> None:
		super().__init__()
		if type(expected_filename) == str:
			expected_filename = [expected_filename]
		self.expected_file = expected_filename
	
	def thread_target(self, client_process: subprocess.Popen, actuator, sync_semaphore: threading.Thread):
		class EventHandler(pyinotify.ProcessEvent):
			def my_init(self): 
				self.expected_file = None
				self.stop_event = None

			def process_IN_MOVED_TO(self, event):
				if self.expected_file is not None and event.name not in self.expected_file:
					return
				logging.info(f'BrowserDownloadWatchdogSensor detected expected file [{event.name}]')
				if self.stop_event is not None:
					self.stop_event.set()
				

		# Browsers seem to create the expected file, then create a temporary file
		# Finally they move the file contents of the temporary file to the expected file
		# This triggers an `IN_MOVED_TO` event, which should signify the end of a download
		wm = pyinotify.WatchManager()
		mask = pyinotify.IN_MOVED_TO
		event_handler = EventHandler()
		notifier = pyinotify.ThreadedNotifier(wm, event_handler)
		event_handler.expected_file = self.expected_file
		event_handler.stop_event = threading.Event()
		notifier.start()
		watched_path = wm.add_watch(self.path_collection.download_path_client, mask)
		try:
			while not self.terminate_sensor and not event_handler.stop_event.is_set():
				if client_process is not None and client_process.poll() is not None:
					logging.info(f'BrowserDownloadWatchdogSensor detected client exit before finding expected file')
					sync_semaphore.release()
					wm.rm_watch(watched_path[self.path_collection.download_path_client])
					notifier.stop()
					return
				time.sleep(1)
		except Exception as e:
			logging.error("BrowserDownloadWatchdogSensor encountered a generic exception, sensor killed")
			logging.error(e)

		wm.rm_watch(watched_path[self.path_collection.download_path_client])
		notifier.stop()
		if self.terminate_sensor:
			logging.info("BrowserDownloadWatchdogSensor stop request handled")
			return
		sync_semaphore.release()
		logging.info('BrowserDownloadWatchdogSensor file-found triggered')
		if client_process is not None:
			client_process.terminate()
		if actuator is not None:
			actuator()