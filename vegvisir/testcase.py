from datetime import date, datetime
from enum import Enum
import tempfile

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