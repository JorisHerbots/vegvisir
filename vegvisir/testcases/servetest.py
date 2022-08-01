from datetime import datetime
from enum import Enum
import tempfile
import subprocess
import sys
import logging
from typing import List
import threading
import time
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .testcase import *

class ServeTest(TestCase):
	file_to_find = "create-name-todo.json"
	timeout_time = 60
	id = "servetest"

	def __init__(self):
		super().__init__()
		self.name = "servetest"
		self.testend = TestEndUntilDownload()

		self._www_dir = StaticDirectory("./www")
		self.request_urls: str = "https://server4/video/bbb/BigBuckBunny_1s_simple_2014_05_09.mpd"

	def testname(self, perspective: Perspective):
		if perspective == Perspective.SERVER:
			return "http3"
		return super().testname(perspective)

	def additional_containers(self) -> List[str]:
		return []#["iperf_server", "iperf_client"]

	def additional_envs(self) -> List[str]:
		return ["IPERF_CONGESTION=cubic"]

	def set_parameters(self, parameters):
		self.request_urls = parameters["request_url"]
		self.timeout = parameters["timeout"]