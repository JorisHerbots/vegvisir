from datetime import date, datetime, time
from enum import Enum
import tempfile
import subprocess
import sys
import logging
from typing import List

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

class TestCase:
	name: str = ""

	origin: str = "193.167.100.100:443"
	request_urls: str = "https://193.167.100.100:443"

	_www_dir = None
	_download_dir = None
	_cert_dir = None

	cert_fingerprint: str = ""
	
	scenario: str = ""
	timeout: int = 60

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
		self.timeout = 300

		self._www_dir = StaticDirectory("./www")
		self.request_urls: str = "https://193.167.100.100:443 https://193.167.100.100:443/test.html"

	def testname(self, perspective: Perspective):
		if perspective == Perspective.SERVER:
			return "http3"
		return super().testname(perspective)

	def additional_containers(self) -> List[str]:
		return ["iperf_server", "iperf_client"]

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