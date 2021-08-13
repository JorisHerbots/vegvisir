from datetime import datetime
import logging
import sys
import subprocess
from typing import List
import json
import tempfile
import re
import shutil
from pathlib import Path

from .implementation import Application, Command, Docker, Image, Scenario, Shaper, Implementation, Role, Type, RunStatus, get_name_from_image, get_repo_from_image, get_tag_from_image
from .testcase import Perspective, ServeTest, StaticDirectory, Status, TestCase, TestResult

class LogFileFormatter(logging.Formatter):
	def format(self, record):
		msg = super(LogFileFormatter, self).format(record)
		# remove color control characters
		return re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]").sub("", msg)

class Runner:
	_start_time: datetime = 0
	_end_time: datetime = 0
	_running: bool = False
	_test_label: str = ""

	_image_repos: List[str] = ["vegvisir"]
	_image_sets: List[str] = []

	_clients: List[Implementation] = []
	_servers: List[Implementation] = []
	_shapers: List[Shaper] = []

	_clients_active: List[Implementation] = []
	_servers_active: List[Implementation] = []
	_shapers_active: List[Shaper] = []

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

			active = False
			if "active" in attrs:
				active = attrs["active"]

			roles = []
			for role in attrs["role"]:
				if role == "client":
					roles.append(Role.CLIENT)
					client_settings = attrs["client"]
					impl = None
					if client_settings["type"] == Type.DOCKER.value:
						impl = Docker(name, attrs["image"], attrs["url"])
					elif client_settings["type"] == Type.APPLICATION.value:
						impl = Application(name, client_settings["command"], attrs["url"])
						if "setup" in client_settings:
							for cmd in client_settings["setup"]:
								scmd = Command()
								scmd.sudo = cmd["sudo"]
								scmd.replace_tilda = cmd["replace_tilda"]
								scmd.command = cmd["command"]
								impl.setup.append(scmd)
					impl.active = active
					self._clients.append(impl)

				elif role == "server":
					roles.append(Role.SERVER)
					impl = Docker(name, attrs["image"], attrs["url"])
					impl.active = active
					self._servers.append(impl)

				elif role == "shaper":
					roles.append(Role.SHAPER)
					impl = Shaper(name, attrs["image"], attrs["url"])
					impl.scenarios = []
					for scenario in  attrs["scenarios"]:
						scen_attrs = attrs["scenarios"][scenario]
						scen = Scenario(scenario, scen_attrs["arguments"])
						if "active" in scen_attrs:
							scen.active = scen_attrs["active"]
						impl.scenarios.append(scen)
					impl.active = active
					self._shapers.append(impl)				

			logging.debug("\tloaded %s as %s", name, attrs["role"])
		self._scan_image_repos()

	def _read_implementations_file(self, file: str):
		self._clients = []
		self._servers = []
		self._shapers = []

		with open(file) as f:
			implementations = json.load(f)

		self.set_implementations(implementations)

	def _scan_image_repos(self):
		proc = subprocess.run(
			"docker images | awk '{print $1, $2}'",
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT
		)
		local_images = proc.stdout.decode('utf-8').replace(' ', ':').split('\n')[1:]
		for img in local_images:
			repo = get_repo_from_image(img)
			if repo in self._image_repos:
				tag = get_tag_from_image(img)
				set_name = get_name_from_image(img)
				if not repo + '/' + set_name in self._image_sets:
					self._image_sets.append(repo + '/' + set_name)
				for x in self._clients + self._servers + self._shapers:
					if hasattr(x, 'image_name') and x.image_name == tag:
						x.images.append(Image(img))

	def run(self) -> int:
		self._running = True
		self._start_time = datetime.now()
		self._log_dir = "logs/{}/{:%Y-%m-%dT%H:%M:%S}".format(self._test_label,self._start_time)
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
		if (out != b'' and not out.startswith(b'[sudo] password for ')) or not err is None:
			logging.debug("enabling ipv6 resulted in non empty output: %s\n%s", out, err)

		#TODO create backup using -b and reset to backup instead of removing entry later
		hosts_proc = subprocess.Popen(
				["sudo", "-S", "hostman", "add", "193.167.100.100", "server4"],
				shell=False,
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
		out, err = hosts_proc.communicate(self._sudo_password.encode())
		logging.debug("append entry to hosts: %s", out.decode('utf-8'))
		if not err is None:
			logging.debug("appending entry to hosts file resulted in error: %s", err)

		self._clients_active = list((x for x in self._clients if x.active))
		self._servers_active = list((x for x in self._servers if x.active))
		self._shapers_active = list((x for x in self._shapers if x.active))

		for x in self._shapers_active + self._servers_active + self._shapers_active:
			x.status = RunStatus.WAITING
			if hasattr(x, 'scenarios'):
				for y in x.scenarios:
					y.status = RunStatus.WAITING

		for shaper in self._shapers_active:
			shaper.status = RunStatus.RUNNING
			for scenario in shaper.scenarios:
				scenario.status = RunStatus.RUNNING
				shaper_images = list((x for x in shaper.images if x.active))
				for shaper_image in shaper_images:
					shaper.curr_image = shaper_image
					for server in self._servers_active:
						server.status = RunStatus.RUNNING
						server_images = list((x for x in server.images if x.active))
						for server_image in server_images:
							server.curr_image = server_image
							for client in self._clients_active:
								client.status = RunStatus.RUNNING

								testcase = ServeTest()
								testcase.scenario = scenario.arguments

								if client.type == Type.DOCKER.value:
									client_images = list((x for x in client.images if x.active))
									for client_image in client_images:
										client.curr_image = client_image
										logging.debug("running with shaper %s (%s) (scenario: %s), server %s (%s), and client %s (%s)",
										shaper.name, shaper_image.url, scenario.arguments,
										server.name, server_image.url,
										client.name, client_image.url
										)

										result = self._run_test(shaper, server, client, testcase)
										logging.debug("\telapsed time since start of test: %s", str(result.end_time - result.start_time))
									
								else:
									logging.debug("running with shaper %s (%s) (scenario: %s), server %s (%s), and client %s",
									shaper.name, shaper_image.url, scenario.arguments,
									server.name, server_image.url,
									client.name
									)

									result = self._run_test(shaper, server, client, testcase)
									logging.debug("\telapsed time since start of test: %s", str(result.end_time - result.start_time))

								client.status = RunStatus.DONE
						server.status = RunStatus.DONE
				scenario.status = RunStatus.DONE
			shaper.status = RunStatus.DONE

		hosts_proc = subprocess.Popen(
				["sudo", "-S", "hostman", "remove", "--names=server4"],
				shell=False,
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
		out, err = hosts_proc.communicate(self._sudo_password.encode())
		logging.debug("remove entry from hosts: %s", out.decode('utf-8'))
		if not err is None:
			logging.debug("removing entry from hosts file resulted in error: %s", err)

		self._end_time = datetime.now()
		logging.info("elapsed time since start of run: %s", str(self._end_time - self._start_time))
		self._running = False
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

			#"CLIENT=" + client.image + " "
			"TESTCASE_CLIENT=" + testcase.testname(Perspective.CLIENT) + " "
			"REQUESTS=\"" + testcase.request_urls + "\"" + " "

			"DOWNLOADS=" + testcase.download_dir() + " "
			"SERVER=" + server.curr_image.url + " "
			"TESTCASE_SERVER=" + testcase.testname(Perspective.SERVER) + " "
			"WWW=" + testcase.www_dir() + " "
			"CERTS=" + testcase.certs_dir() + " "

			"SHAPER=" + shaper.curr_image.url + " "
			"SCENARIO=" + testcase.scenario + " "

			"SERVER_LOGS=" + "/logs" + " "
			"CLIENT_LOGS=" + "/logs" + " "
		)
		params += " ".join(testcase.additional_envs())
		containers = "sim server " + " ".join(testcase.additional_containers())

		cmd = (
			params
			+ " docker-compose up -d "
			+ containers
		)

		result.status = Status.FAILED
		try:
			# Setup client
			if client.type == Type.APPLICATION:
				for setup_cmd in client.setup:
					out = ""
					if setup_cmd.replace_tilda:
						setup_cmd.command = setup_cmd.command.replace("~", str(Path.home()))
					if setup_cmd.sudo:
						net_proc = subprocess.Popen(
						["sudo", "-S"] + setup_cmd.command.split(" "),
						shell=False,
						stdin=subprocess.PIPE,
						stdout=subprocess.PIPE,
						stderr=subprocess.STDOUT
					)
						o, e = net_proc.communicate(self._sudo_password.encode())
						out += str(o) + "\n" + str(e)
					else:
						proc = subprocess.run(
							setup_cmd.command,
							shell=True,
							stdout=subprocess.PIPE,
							stderr=subprocess.STDOUT
						)
						out += proc.stdout.decode("utf-8")
					logging.debug("client setup: %s", out)

			# Setup server and network
			#TODO exit on error
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
			client_cmd = ""
			if client.type == Type.DOCKER:
				params += "CLIENT=" + client.curr_image.url + " "
				client_cmd = (
					params
					+ " docker-compose up --abort-on-container-exit --timeout 1 "
					+ "client"
				)
			elif client.type == Type.APPLICATION:
				client_cmd = client.command.format(origin=testcase.origin, cert_fingerprint=testcase.cert_fingerprint, request_urls=testcase.request_urls)

			logging.debug("running client: %s", client_cmd)
			try:
				client_proc = subprocess.run(
					client_cmd,
					shell=True,
					stdout=subprocess.PIPE,
					stderr=subprocess.STDOUT,
					timeout=testcase.timeout
				)
				logging.debug("%s", client_proc.stdout.decode("utf-8"))
			except KeyboardInterrupt as e:
				logging.debug("manual interrupt")
			# Wait for tests
			# try:
			# 	#TODO use threading instead? wait for events? how to do infinite sleep?
			# 	time.sleep(testcase.timeout) #TODO get from testcase
			# 	raise subprocess.TimeoutExpired(cmd, testcase.timeout, proc.stdout, proc.stderr)
			# except KeyboardInterrupt as e:
			# 	logging.debug("manual interrupt")
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
		if client.type == Type.DOCKER:
			self._copy_logs("client", client_log_dir)
		self._copy_logs("server", server_log_dir)

		# save logs
		logging.getLogger().removeHandler(log_handler)
		log_handler.close()
		if result.status == Status.FAILED or result.status == Status.SUCCES:
			log_dir = self._log_dir + "/"
			if client.type == Type.DOCKER:
				log_dir = log_dir + server.curr_image.repo + "_" + server.curr_image.name + "_" + server.curr_image.tag + "_" +  client.curr_image.repo + "_" + client.curr_image.name + "_" + client.curr_image.tag + "/" + testcase.name
			else:
				log_dir = log_dir + server.curr_image.repo + "_" + server.curr_image.name + "_" + server.curr_image.tag + "_" + client.name + "/" + testcase.name
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