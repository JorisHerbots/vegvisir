from datetime import datetime
import logging
import sys
from typing import List
import json

from .implementation import Implementation, Role

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

		self._end_time = datetime.now()
		logging.info("elapsed time since start of run: %s", str(self._end_time - self._start_time))
		return nr_failed