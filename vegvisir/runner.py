from datetime import datetime
import logging
import sys
from typing import List

from .implementation import Implementation

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