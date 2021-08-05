from datetime import datetime
import logging
import sys
import subprocess
from typing import List
import json

from .implementation import Implementation, Role
from .testcase import TestResult

class Runner:
	_start_time: datetime = 0
	_end_time: datetime = 0

	_clients: List[Implementation] = []
	_servers: List[Implementation] = []
	_shapers: List[Implementation] = []

	_logger: logging.Logger = None
	_debug: bool = False

	def __init__(
		self,
		implementations_file: str,
		debug: bool = False
	):
		self._logger = logging.getLogger()
		self._logger.setLevel(logging.DEBUG)
		console = logging.StreamHandler(stream=sys.stderr)
		if debug:
			console.setLevel(logging.DEBUG)
		else:
			console.setLevel(logging.INFO)
		self._logger.addHandler(console)

		self._read_implementations_file(implementations_file)

	def _read_implementations_file(self, file: str):
		self._clients = []
		self._servers = []
		self._shapers = []

		with open(file) as f:
			implementations = json.load(f)

		logging.debug("Loading implementations:")
		
		for name in implementations:
			attrs = implementations[name]

			roles = []
			to_add = []
			for role in attrs["role"]:
				if role == "client":
					roles.append(Role.CLIENT)
					to_add.append(self._clients)
				elif role == "server":
					roles.append(Role.SERVER)
					to_add.append(self._servers)
				elif role == "shaper":
					roles.append(Role.SHAPER)
					to_add.append(self._shapers)

			impl = Implementation(name, attrs["image"], attrs["url"], roles)

			for lst in to_add:
				lst.append(impl)

			logging.debug("\tloaded %s as %s", name, attrs["role"])

	def run(self) -> int:
		self._start_time = datetime.now()
		nr_failed = 0

		for shaper in self._shapers:
			for server in self._servers:
				for client in self._clients:
					logging.debug("running with shaper %s (%s), server %s (%s), and client %s (%s)",
					shaper.name, shaper.image,
					server.name, server.image,
					client.name, client.image
					)

					result = self._run_test(shaper, server, client)
					logging.debug("\telapsed time since start of test: %s", str(result.end_time - result.start_time))

		self._end_time = datetime.now()
		logging.info("elapsed time since start of run: %s", str(self._end_time - self._start_time))
		return nr_failed

	def _run_test(
		self,
		shaper: Implementation,
		server: Implementation, 
		client: Implementation
		) -> TestResult:
		result = TestResult()
		result.start_time = datetime.now()

		params = (
			"CLIENT=" + client.image + " "
			"CLIENT_PARAMS=\"--ca-certs tests/pycacert.pem https://193.167.100.100:4433/\"" + " "
			"DOWNLOADS=" + "/" + " "
			"SERVER=" + server.image + " "
			"SERVER_PARAMS=\"--certificate tests/ssl_cert.pem --private-key tests/ssl_key.pem\"" + " "
			"SHAPER=" + shaper.image + " "
			"SCENARIO=\"simple-p2p --delay=15ms --bandwidth=10Mbps --queue=25\"" + " "
		)
		containers = "sim client server"

		cmd = (
			params
			+ " docker-compose up --abort-on-container-exit --timeout 1 "
			+ containers
		)

		try:
			proc = subprocess.run(
				cmd,
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				timeout=30
			)
			logging.debug("proc: %s", proc.stdout.decode("utf-8"))
		except subprocess.TimeoutExpired as e:
			logging.debug("subprocess timeout: %s", e.stdout.decode("utf-8"))
		except Exception as e:
			logging.debug("subprocess error: %s", str(e))

		result.end_time = datetime.now()
		return result