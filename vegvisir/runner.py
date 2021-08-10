from datetime import datetime
import logging
import sys
import subprocess
from typing import List
import json
import tempfile
import re
import shutil
import time

from .implementation import Shaper, Implementation, Role
from .testcase import Perspective, ServeTest, Status, TestCase, TestResult

class LogFileFormatter(logging.Formatter):
	def format(self, record):
		msg = super(LogFileFormatter, self).format(record)
		# remove color control characters
		return re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]").sub("", msg)

class Runner:
	_start_time: datetime = 0
	_end_time: datetime = 0

	_clients: List[Implementation] = []
	_servers: List[Implementation] = []
	_shapers: List[Shaper] = []

	_sudo_password: str = ""

	_logger: logging.Logger = None
	_debug: bool = False
	_save_files: bool = False
	_log_dir: str = ""

	def __init__(
		self,
		sudo_password: str = "",
		debug: bool = False,
		save_files: bool = False
	):
		self._sudo_password = sudo_password
		self._debug = debug
		self._save_files = save_files

		self._logger = logging.getLogger()
		self._logger.setLevel(logging.DEBUG)
		console = logging.StreamHandler(stream=sys.stderr)
		if self._debug:
			console.setLevel(logging.DEBUG)
		else:
			console.setLevel(logging.INFO)
		self._logger.addHandler(console)

	def logger(self):
		return self._logger

	def set_sudo_password(self, sudo_password: str):
		self._sudo_password = sudo_password

	def set_implementations_from_file(self, file: str):
		self._read_implementations_file(file)

	def set_implementations(self, implementations):
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

			impl = None
			if Role.SHAPER in roles:
				impl = Shaper(name, attrs["image"], attrs["url"], roles)
				impl.scenarios = attrs["scenarios"]
			else:
				impl = Implementation(name, attrs["image"], attrs["url"], roles)

			for lst in to_add:
				lst.append(impl)

			logging.debug("\tloaded %s as %s", name, attrs["role"])

	def _read_implementations_file(self, file: str):
		self._clients = []
		self._servers = []
		self._shapers = []

		with open(file) as f:
			implementations = json.load(f)

		self.set_implementations(implementations)

	def run(self) -> int:
		self._start_time = datetime.now()
		self._log_dir = "logs/{:%Y-%m-%dT%H:%M:%S}".format(self._start_time)
		nr_failed = 0

		#enable ipv6 support
		#sudo modprobe ip6table_filter
		ipv6_proc = subprocess.Popen(
				["sudo", "-S", "modprobe", "ip6table_filter"],
				shell=False,
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
		out, err = ipv6_proc.communicate(self._sudo_password.encode())
		if out != b'' or not err is None:
			logging.debug("enabling ipv6 resulted in non empty output: %s\n%s", out, err)

		for shaper in self._shapers:
			for scenario in shaper.scenarios:
				for server in self._servers:
					for client in self._clients:
						logging.debug("running with shaper %s (%s) (scenario: %s), server %s (%s), and client %s (%s)",
						shaper.name, shaper.image, scenario,
						server.name, server.image,
						client.name, client.image
						)

						testcase = ServeTest()
						testcase.scenario = scenario

						result = self._run_test(shaper, server, client, testcase)
						logging.debug("\telapsed time since start of test: %s", str(result.end_time - result.start_time))

		self._end_time = datetime.now()
		logging.info("elapsed time since start of run: %s", str(self._end_time - self._start_time))
		return nr_failed

	def _run_test(
		self,
		shaper: Implementation,
		server: Implementation, 
		client: Implementation,
		testcase: TestCase
		) -> TestResult:
		result = TestResult()
		result.start_time = datetime.now()

		sim_log_dir = tempfile.TemporaryDirectory(dir="/tmp", prefix="logs_sim_")
		server_log_dir = tempfile.TemporaryDirectory(dir="/tmp", prefix="logs_server_")
		client_log_dir = tempfile.TemporaryDirectory(dir="/tmp", prefix="logs_client_")
		log_file = tempfile.NamedTemporaryFile(dir="/tmp", prefix="output_log_")
		log_handler = logging.FileHandler(log_file.name)
		log_handler.setLevel(logging.DEBUG)

		formatter = LogFileFormatter("%(asctime)s %(message)s")
		log_handler.setFormatter(formatter)
		logging.getLogger().addHandler(log_handler)

		params = (
			"WAITFORSERVER=server:443 "

			"CLIENT=" + client.image + " "
			"TESTCASE_CLIENT=" + testcase.testname(Perspective.CLIENT) + " "
			"REQUESTS=\"https://193.167.100.100:443/\"" + " "

			"DOWNLOADS=" + testcase.download_dir() + " "
			"SERVER=" + server.image + " "
			"TESTCASE_SERVER=" + testcase.testname(Perspective.SERVER) + " "
			"WWW=" + testcase.www_dir() + " "
			"CERTS=" + testcase.certs_dir() + " "

			"SHAPER=" + shaper.image + " "
			"SCENARIO=" + testcase.scenario + " "

			"SERVER_LOGS=" + "/logs" + " "
			"CLIENT_LOGS=" + "/logs" + " "
		)
		params += " ".join(testcase.additional_envs())
		containers = "sim client server " + " ".join(testcase.additional_containers())

		cmd = (
			params
			+ " docker-compose up -d "
			+ containers
		)

		result.status = Status.FAILED
		try:
			# Setup server and network
			logging.debug("running command: %s", cmd)
			proc = subprocess.run(
				cmd,
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
			
			net_proc = subprocess.Popen(
				["sudo", "-S", "ip", "route", "del", "193.167.100.0/24"],
				shell=False,
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
			out, err = net_proc.communicate(self._sudo_password.encode())
			logging.debug("network setup: %s", out.decode("utf-8"))
			if not err is None:
				logging.debug("network error: %s", err.decode("utf-8"))
			net_proc = subprocess.Popen(
				["sudo", "-S", "ip", "route", "add", "193.167.100.0/24", "via", "193.167.0.2"],
				shell=False,
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
			out, err = net_proc.communicate(self._sudo_password.encode())
			logging.debug("network setup: %s", out.decode("utf-8"))
			if not err is None:
				logging.debug("network error: %s", err.decode("utf-8"))
			net_proc = subprocess.Popen(
				["sudo", "-S", "./veth-checksum.sh"],
				shell=False,
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
			out, err = net_proc.communicate(self._sudo_password.encode())
			logging.debug("network setup: %s", out.decode("utf-8"))
			if not err is None:
				logging.debug("network error: %s", err.decode("utf-8"))

			# Setup client
			#TODO
			# Wait for tests
			try:
				#TODO use threading instead? wait for events? how to do infinite sleep?
				time.sleep(testcase.timeout) #TODO get from testcase
				raise subprocess.TimeoutExpired(cmd, testcase.timeout, proc.stdout, proc.stderr)
			except KeyboardInterrupt as e:
				logging.debug("manual interrupt")
			logging.debug("proc: %s", proc.stdout.decode("utf-8"))
			proc = subprocess.run(
				"docker-compose logs -t",
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
			logging.debug("%s", proc.stdout.decode("utf-8"))
			result.status = Status.SUCCES
		except subprocess.TimeoutExpired as e:
			logging.debug("subprocess timeout: %s", e.stdout.decode("utf-8"))
		except Exception as e:
			logging.debug("subprocess error: %s", str(e))

		self._copy_logs("sim", sim_log_dir)
		self._copy_logs("client", client_log_dir)
		self._copy_logs("server", server_log_dir)

		# save logs
		logging.getLogger().removeHandler(log_handler)
		log_handler.close()
		if result.status == Status.FAILED or result.status == Status.SUCCES:
			log_dir = self._log_dir + "/" + server.name + "_" + client.name + "/" + testcase.name
			shutil.copytree(server_log_dir.name, log_dir + "/server")
			shutil.copytree(client_log_dir.name, log_dir + "/client")
			shutil.copytree(sim_log_dir.name, log_dir + "/sim")
			shutil.copyfile(log_file.name, log_dir + "/output.txt")
			if self._save_files and result.status == Status.FAILED:
				shutil.copytree(testcase.www_dir(), log_dir + "/www")
				try:
					shutil.copytree(testcase.download_dir(), log_dir + "/downloads")
				except Exception as exception:
					logging.info("Could not copy downloaded files: %s", exception)

		server_log_dir.cleanup()
		client_log_dir.cleanup()
		sim_log_dir.cleanup()

		try:
			logging.debug("shutting down containers")
			proc = subprocess.run(
				"docker-compose down",
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
			logging.debug("shut down successful: %s", proc.stdout.decode("utf-8"))
		except Exception as e:
			logging.debug("subprocess error while shutting down: %s", str(e))

		result.end_time = datetime.now()
		return result


	def _copy_logs(self, container: str, dir: tempfile.TemporaryDirectory):
		r = subprocess.run(
			'docker cp "$(docker-compose --log-level ERROR ps -q '
			+ container
			+ ')":/logs/. '
			+ dir.name,
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
		)
		if r.returncode != 0:
			logging.info(
				"Copying logs from %s failed: %s", container, r.stdout.decode("utf-8")
			)