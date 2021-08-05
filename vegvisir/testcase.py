from datetime import date, datetime
from enum import Enum
import tempfile
import subprocess
import sys
import logging

class Status(Enum):
	SUCCES = 1
	FAILED = 2

class TestResult:
	start_time: datetime = 0
	end_time: datetime = 0
	status: Status = Status.FAILED

	def __init__(self):
		pass

class TestCase:
	name: str= ""
	_www_dir = None
	_download_dir = None
	_cert_dir = None

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
			generate_cert_chain(self._cert_dir.name)
		return self._cert_dir.name + "/"

def generate_cert_chain(directory: str, length: int = 1):
    cmd = "./certs.sh " + directory + " " + str(length)
    r = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    logging.debug("%s", r.stdout.decode("utf-8"))
    if r.returncode != 0:
        logging.info("Unable to create certificates")
        sys.exit(1)