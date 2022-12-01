from curses.ascii import isdigit
from datetime import datetime
from distutils.command.config import config
import logging
import os
import pathlib
import shlex
import sys
import subprocess
from time import time, sleep
from typing import Dict, List, Set, Tuple
import json
import tempfile
import re
import shutil
from pathlib import Path
from vegvisir import environments
from vegvisir.data import ExperimentPaths
from vegvisir.environments.base_environment import BaseEnvironment

# from vegvisir.environments.base_environment import BaseEnvironment, TimeoutSensor, WebserverBasic

from .implementation import DockerImage, Parameters, HostCommand, Endpoint, Scenario, Shaper, VegvisirCommandException

class VegvisirException(Exception):
	pass

class VegvisirInvalidImplementationConfigurationException(Exception):
	pass

class VegvisirInvalidExperimentConfigurationException(Exception):
	pass

class VegvisirCommandExecutionException(Exception):
	pass

class LogFileFormatter(logging.Formatter):
	def format(self, record):
		msg = super(LogFileFormatter, self).format(record)
		# remove color control characters
		return re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]").sub("", msg)

class Runner:
	# _start_time: datetime = 0
	# _end_time: datetime = 0
	# _running: bool = False
	# _test_label: str = ""
	# _test_repetitions: int = 1
	# _curr_repetition: int = 1

	# _image_repos: List[str] = ["vegvisir"]
	# _image_sets: List[str] = []

	# _clients: dict[str, Implementation] = {}
	# _servers: dict[str, Implementation] = {}
	# _shapers: dict[str, Shaper] = {}
	# _tests: List[TestCaseWrapper] = []

	# _clients_active: List[Implementation] = []
	# _servers_active: List[Implementation] = []
	# _shapers_active: List[Shaper] = []
	# _tests_active: List[TestCase] = []

	# _sudo_password: str = ""

	# _logger: logging.Logger = None
	# _debug: bool = False
	# _save_files: bool = False
	# _log_dir: str = ""



	def __init__(self, sudo_password: str = "", debug: bool = False, save_files: bool = False, implementations_file_path: str = None):
		self._path_collection = ExperimentPaths()
		
		self._client_endpoints: Dict[str, Endpoint] = {}
		self._server_endpoints: Dict[str, Endpoint] = {}
		self._shapers: Dict[str, Shaper] = {}

		self._client_configurations: List[Dict] = []
		self._server_configurations: List[Dict] = []
		self._shaper_configurations: List[Dict] = []

		self.www_path = None

		self.iterations = 1

		self.environment: BaseEnvironment = None

		self._sudo_password = sudo_password
		self._debug = debug
		# self._save_files = save_files

		self._logger = logging.getLogger()
		self._logger.setLevel(logging.DEBUG)
		console = logging.StreamHandler(stream=sys.stderr)
		if self._debug:
			console.setLevel(logging.DEBUG)
		else:
			console.setLevel(logging.INFO)
		self._logger.addHandler(console)

		# Explicit check so we don't keep trigger an auth lock
		if not self._is_sudo_password_valid():
			raise VegvisirException("Authentication with sudo failed. Provided password is wrong?")

		if implementations_file_path:
			self.load_implementations_from_file(implementations_file_path)

		# TODO jherbots redo namings here, leave for now
		# for t in TESTCASES:
			# tw = TestCaseWrapper()
			# tw.testcase = t()
			# self._tests.append(tw)

	def logger(self):
		return self._logger

	def set_sudo_password(self, sudo_password: str):
		self._sudo_password = sudo_password

	def spawn_subprocess(self, command: str, shell: bool = False) -> Tuple[str, str]:
		if shell:
			proc = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		else:
			shlex_command = shlex.split(command)
			proc = subprocess.Popen(shlex_command, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		proc_input = self._sudo_password.encode() if "sudo" in command else None
		if proc_input is not None:
			out, err = proc.communicate(input=proc_input)
		return out, err, proc

	def spawn_parallel_subprocess(self, command: str, root_privileges: bool = False, shell: bool = False) -> subprocess.Popen:
		shell = shell == True
		if root_privileges:
			# -Skp makes it so sudo reads input from stdin, invalidates the privileges granted after the command is ran and removes the password prompt
			# Removing the password prompt and invalidating the sessions removes the complexity of having to check for the password prompt, we know it'll always be there
			command = "sudo -Skp '' " + command
		debug_command = command
		command = shlex.split(command) if shell == False else command
		proc = subprocess.Popen(command, shell=shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		if root_privileges:
			try:
				proc.stdin.write(self._sudo_password.encode())
			except BrokenPipeError:
				logging.error(f"Pipe broke before we could provide sudo credentials. No sudo available? [{debug_command}]")
		return proc

	def spawn_blocking_subprocess(self, command: str, root_privileges: bool = False, shell: bool = False) -> Tuple[subprocess.Popen, str, str]:
		proc = self.spawn_parallel_subprocess(command, root_privileges, shell)
		out, err = proc.communicate()
		return proc, out.decode("utf-8"), err.decode("utf-8")

	def _is_sudo_password_valid(self):
		proc, _, _ = self.spawn_blocking_subprocess("which sudo", True, False)
		return proc.returncode == 0

	def load_implementations_from_file(self, implementations_path: str):
		"""
		Load client, shaper and server implementations from JSON file
		Warning: Calling this function will overwrite current list of implementations!
		"""
		self._client_endpoints = {}
		self._server_endpoints = {}
		self._shapers = {}

		try:
			with open(implementations_path) as f:
				implementations = json.load(f)
			self._load_implementations_from_json(implementations)
			self._path_collection.implementations_configuration_file_path = implementations_path
		except json.JSONDecodeError as e:
			logging.error(f"Failed to decode provided implementations JSON [{implementations_path}] | {e}")

	# def _check_implementation_existance(self, name: str, implementation_list: list[Implementation]):
	# 	"""
	# 	O(n)
	# 	TODO jherbots Needed? 
	# 	"""
	# 	for impl in implementation_list:
	# 		if impl.name == name:
	# 			print(name)
	# 			return True
	# 	return False

	def _load_implementations_from_json(self, implementations):
		"""
		Load implementation from a JSON file
		If truly loaded via json.load, duplicates will be automatically be eliminated
		"""
		CLIENTS_KEY = "clients"
		SERVERS_KEY = "servers"
		SHAPERS_KEY = "shapers"
		logging.debug("Vegvisir: Loading implementations:")
		
		if not all(key in implementations for key in [CLIENTS_KEY, SERVERS_KEY, SHAPERS_KEY]):
			raise VegvisirInvalidImplementationConfigurationException("Loading implementations halted. One or multiple keys are missing in the provided implementations JSON ('clients', 'servers' and/or 'shapers').") 
		
		# Clients
		for client, configuration in implementations[CLIENTS_KEY].items():
			if "image" in configuration and "command" in configuration:
				raise VegvisirInvalidImplementationConfigurationException(f"Client [{client}] contains both docker and host setup keys.")
			impl = None
			if "image" in configuration or "command" in configuration:
				implementation_type = Endpoint.Type.DOCKER if "image" in configuration else Endpoint.Type.HOST
				parameters = Parameters(configuration.get("parameters", []))
				impl = Endpoint(client, client, implementation_type, DockerImage(configuration["image"]) if implementation_type == Endpoint.Type.DOCKER else HostCommand(configuration["command"]), parameters)  # TODO jherbots pretty name
				if implementation_type == Endpoint.Type.HOST:
					try:
						impl.command.serialize_command(parameters.hydrate_with_empty_arguments())
					except VegvisirCommandException as e:
						raise VegvisirInvalidImplementationConfigurationException(f"Client [{client}] command contains unknown parameters, dry run failed => {e}")
				if "setup" in configuration:
					if implementation_type == Endpoint.Type.DOCKER:
						raise VegvisirInvalidImplementationConfigurationException(f"Client [{client}] represents a containerized configuration, these can not contain a 'setup' key.")
					for index, task in enumerate(configuration["setup"]):
						if "command" not in task:
							raise VegvisirInvalidImplementationConfigurationException(f"Setup task #{index} of client [{client}] does not contain the 'command' entry.")
						impl.setup.append(HostCommand(task["command"], task.get("root_required", False)))
			
			if not impl:
				raise VegvisirInvalidImplementationConfigurationException(f"Client [{client}] does not contain an 'image' or 'command' entry.")
			self._client_endpoints[client] = impl

		# Server
		for server, configuration in implementations[SERVERS_KEY].items():
			if not "image" in configuration:
				raise VegvisirInvalidImplementationConfigurationException(f"Server [{server}] missing key 'image'.")
			parameters = Parameters(configuration.get("parameters", []))
			impl = Endpoint(server, server, Endpoint.Type.DOCKER, DockerImage(configuration["image"]), parameters)
			self._server_endpoints[server] = impl

		# Shapers
		for shaper, configuration in implementations[SHAPERS_KEY].items():
			SCENARIOS_KEY = "scenarios"
			if not "image" in configuration:
				raise VegvisirInvalidImplementationConfigurationException(f"Shaper [{shaper}] missing key 'image'.")
			if SCENARIOS_KEY not in configuration:
				raise VegvisirInvalidImplementationConfigurationException(f"Shaper [{shaper}] does not contain any scenarios.")

			impl = Shaper(shaper, shaper, DockerImage(configuration["image"]))  # TODO pretty name
			for scenario, contents in configuration[SCENARIOS_KEY].items():
				if type(contents) == str:
					impl.scenarios[scenario] = Scenario(contents, Parameters())
				elif contents.get("command") and contents.get("parameters"):
					parameters = Parameters(contents.get("parameters", []))
					impl.scenarios[scenario] = Scenario(contents["command"], parameters)
				else:
					raise VegvisirInvalidImplementationConfigurationException(f"Shaper [{shaper}] scenario [{scenario}] is not a string or does not contain a 'command' and 'parameters' key. Ignoring scenario entry.")
			self._shapers[shaper] = impl
		
		# print(self._client_endpoints)
		# print(self._server_endpoints)
		# print(self._shapers)
		# for shaper in self._shapers.values():
			# print(shaper.scenarios)
	# 	for name in implementations:
	# 		attrs = implementations[name]

	# 		active = False
	# 		if "active" in attrs:
	# 			active = attrs["active"]

	# 		env = []
	# 		if "env" in attrs:
	# 			env = attrs["env"]

	# 		roles = []
	# 		for role in attrs["role"]:
	# 			if role == "client":
	# 				roles.append(Role.CLIENT)
	# 				client_settings = attrs["client"]
	# 				impl = None
	# 				if client_settings["type"] == Type.DOCKER.value:
	# 					impl = Docker(name, attrs["image"], attrs["url"])
	# 				elif client_settings["type"] == Type.APPLICATION.value:
	# 					impl = Application(name, client_settings["command"], attrs["url"])
	# 					if "setup" in client_settings:
	# 						for cmd in client_settings["setup"]:
	# 							scmd = Command()
	# 							scmd.sudo = cmd["sudo"]
	# 							scmd.replace_tilde = cmd["replace_tilde"]
	# 							scmd.command = cmd["command"]
	# 							impl.setup.append(scmd)
	# 				impl.active = active
	# 				impl.env_vars = env
	# 				impl.role = Role.CLIENT
	# 				self._clients.append(impl)

	# 			elif role == "server":
	# 				roles.append(Role.SERVER)
	# 				impl = Docker(name, attrs["image"], attrs["url"])
	# 				impl.active = active
	# 				impl.env_vars = env
	# 				impl.role = Role.SERVER
	# 				self._servers.append(impl)

	# 			elif role == "shaper":
	# 				roles.append(Role.SHAPER)
	# 				impl = Shaper(name, attrs["image"], attrs["url"])
	# 				impl.scenarios = []
	# 				if "scenarios" in attrs:
	# 					for scenario in  attrs["scenarios"]:
	# 						scen_attrs = attrs["scenarios"][scenario]
	# 						scen = Scenario(scenario, scen_attrs["arguments"])
	# 						if "active" in scen_attrs:
	# 							scen.active = scen_attrs["active"]
	# 						impl.scenarios.append(scen)
	# 				impl.active = active
	# 				impl.env_vars = env
	# 				impl.role = Role.SHAPER
	# 				self._shapers.append(impl)

	# 		logging.debug("Vegvisir: \tloaded %s as %s", name, attrs["role"])
	# 	self._scan_image_repos()

	def load_experiment_from_file(self, file_path: str) -> None:
		# TODO jherbots save config to somewhere
		try:
			with open(file_path) as f:
				configuration = json.load(f)
			self._load_and_validate_experiment_from_json(configuration)
			self._path_collection.experiment_configuration_file_path = file_path
		except json.JSONDecodeError as e:
			raise VegvisirInvalidExperimentConfigurationException(f"Failed to decode experiment configuration JSON [{file_path}] | {e}")

	def _load_and_validate_experiment_from_json(self, configuration):
		"""
		Load and validate is a bad smell, but then again why bother :)
		"""
		CLIENTS_KEY = "clients"
		SERVERS_KEY = "servers"
		SHAPERS_KEY = "shapers"

		if not type(configuration) is dict:
			raise VegvisirInvalidExperimentConfigurationException("Configuration is not a valid JSON dictionary.")

		settings = configuration.get("settings", {})

		playground_mode = settings.get("playground", False)  # Todo implement
		if not playground_mode and not all(key in configuration for key in [CLIENTS_KEY, SERVERS_KEY, SHAPERS_KEY]):
			raise VegvisirInvalidExperimentConfigurationException("Configuration requires 'clients', 'servers' en 'shapers' keys to be set.")
		if playground_mode and not SERVERS_KEY in configuration:
			raise VegvisirInvalidExperimentConfigurationException("Playground mode requires the 'servers' key to be present.")

		def _namecheck_dict(impl_configuration: Dict, impl_entry_index: int, debug_str: str, entries: Dict[str, Endpoint | Shaper]):
			if "name" not in impl_configuration:
				raise VegvisirInvalidExperimentConfigurationException(f"{debug_str.capitalize()} entry #{impl_entry_index} does not contain the 'name' key.")
			if impl_configuration["name"] not in entries:
				raise VegvisirInvalidExperimentConfigurationException(f"{debug_str.capitalize()} [{impl_configuration['name']}] is an unknown {debug_str} implementation.")

		def _parametercheck_endpoint(endpoint_obj: Endpoint, endpoint_configuration: Dict, debug_str: str):
			if len(endpoint_obj.parameters._required_params) > 0 and not endpoint_configuration.get("arguments"):
				raise VegvisirInvalidExperimentConfigurationException(f"{debug_str.capitalize()} [{endpoint_configuration['name']}] requires an 'arguments' entry.")
			valid_input, missing_required_parameters, invalid_parameters = endpoint_obj.parameters.can_input_fit_arguments(endpoint_configuration.get("arguments", {}).keys() if type(endpoint_configuration.get("arguments")) == dict else [])
			if not valid_input:
				raise VegvisirInvalidExperimentConfigurationException(f"{debug_str.capitalize()} [{endpoint_configuration['name']}] is missing required parameters {missing_required_parameters} | The following arguments were unknown and ignored {invalid_parameters}")

		def _scenariocheck_shaper(shaper_configuration: Dict, impl_known_scenarios: Dict[str, Scenario]):
			if shaper_configuration.get("scenario") is None:
				raise VegvisirInvalidExperimentConfigurationException(f"Shaper [{shaper_configuration['name']}] does not contain a 'scenario' entry.")
			if shaper_configuration["scenario"] not in impl_known_scenarios.keys():
				raise VegvisirInvalidExperimentConfigurationException(f"Shaper [{shaper_configuration['name']}] scenario [{shaper_configuration['scenario']}] does not exist in the currently loaded implementation configuration.")
			
			if len(impl_known_scenarios[shaper_configuration["scenario"]].parameters._required_params) > 0:
				if shaper_configuration.get("arguments") is None or type(shaper_configuration["arguments"]) is not dict:
					raise VegvisirInvalidExperimentConfigurationException(f"Shaper [{shaper_configuration['name']}] scenario [{shaper_configuration['scenario']}] requires 'arguments' dictionary.")
				valid_input, missing_required_parameters, invalid_parameters = impl_known_scenarios[shaper_configuration["scenario"]].parameters.can_input_fit_arguments(shaper_configuration["arguments"].keys() if type(shaper_configuration["arguments"]) == dict else [])
				if not valid_input:
					if len(invalid_parameters) > 0:
						raise VegvisirInvalidExperimentConfigurationException(f"Shaper [{shaper_configuration['name']}] is missing required parameters {missing_required_parameters} | The following arguments were unknown and ignored {invalid_parameters}")
					raise VegvisirInvalidExperimentConfigurationException(f"Shaper [{shaper_configuration['name']}] is missing required parameters {missing_required_parameters}")

		def _duplicate_check(name: str, log_name: str | None, entries: Set[str], debug_str: str):
			if log_name is not None:
				if log_name in entries:
					raise VegvisirInvalidExperimentConfigurationException(f"{debug_str.capitalize()} [{name}] its log name [{log_name}] is not unique.")
			else:
				if name in entries:
					raise VegvisirInvalidExperimentConfigurationException(f"{debug_str.capitalize()} [{name}] duplicate detected. Please provide a 'log_name' to be able to distinguish.")


		duplicate_check = set()
		for index, client in enumerate(configuration[CLIENTS_KEY]):
			_namecheck_dict(client, index, "client", self._client_endpoints)
			_duplicate_check(client["name"], client.get("log_name"), duplicate_check, "client")
			duplicate_check.add(client["log_name"] if client.get("log_name") is not None else client["name"])
			_parametercheck_endpoint(self._client_endpoints[client["name"]], client, "client")
			self._client_configurations.append(client)

		duplicate_check = set()
		for index, server in enumerate(configuration[SERVERS_KEY]):
			_namecheck_dict(server, index, "server", self._server_endpoints)
			_duplicate_check(server["name"], server.get("log_name"), duplicate_check, "server")
			duplicate_check.add(server["log_name"] if server.get("log_name") is not None else server["name"])
			_parametercheck_endpoint(self._server_endpoints[server["name"]], server, "server")
			self._server_configurations.append(server)

		duplicate_check = set()
		for index, shaper in enumerate(configuration[SHAPERS_KEY]):
			_namecheck_dict(shaper, index, "shaper", self._shapers)
			_duplicate_check(shaper["name"], shaper.get("log_name"), duplicate_check, "shaper")
			duplicate_check.add(shaper["log_name"] if shaper.get("log_name") is not None else shaper["name"])
			_scenariocheck_shaper(shaper, self._shapers[shaper["name"]].scenarios)
			self._shaper_configurations.append(shaper)

		if settings.get("log_dir") is not None:
			log_dir_root = os.path.abspath(os.path.join(settings["log_dir"], "{}/"))
		else:
			log_dir_root = os.path.abspath("logs/{}/")
		self._path_collection.log_path_root = log_dir_root.format(settings.get("label", "_unidentified"))

		if settings.get("www_dir") is not None:
			self.www_path = os.path.abspath(settings["www_dir"])
		else:
			self.www_path = os.path.join(os.getcwd(), "www")
		if not os.path.exists(self.www_path):
			raise VegvisirInvalidExperimentConfigurationException(f"WWW path does not exist [{self.www_path}]")

		iterations = settings.get("iterations", 1)
		if type(iterations) is str and not iterations.isdigit():
			raise VegvisirInvalidExperimentConfigurationException("Setting 'iterations' must be > 0.")
		try:
			self.iterations = int(iterations)
		except ValueError:
			raise VegvisirInvalidExperimentConfigurationException("Setting 'iterations' must be > 0.")
		if self.iterations <= 0:
			raise VegvisirInvalidExperimentConfigurationException("Setting 'iterations' must be > 0.")

		environment = configuration.get("environment")
		if environment is None:
			raise VegvisirInvalidExperimentConfigurationException("No 'environment' key was found.")
		environment_name = environment.get("name", environments.default_environment)
		if environment_name not in environments.available_environments.keys():
			raise VegvisirInvalidExperimentConfigurationException(f"Environment [{environment_name}] does not exist. Make sure it is correctly loaded in the __init__ file of the environments module.")
		self.environment = environments.available_environments[environment_name]()
				
		environment_sensors = environment.get("sensors")
		if environment_sensors is None:
			raise VegvisirInvalidExperimentConfigurationException("Environment expects the key 'sensors' to be present.")
		for index, sensor in enumerate(environment_sensors):
			if sensor.get("name") is None:
				raise VegvisirInvalidImplementationConfigurationException(f"Sensor #{index} has no 'name' key.")
			if sensor["name"] not in environments.available_sensors:
				raise VegvisirInvalidImplementationConfigurationException(f"Sensor [{sensor['name']}] is unknown. Make sure it is correctly loaded in the __init__ file of the environments module.")
			try:
				# Shallow copy should be fine
				sensor_arguments = sensor.copy()
				del sensor_arguments["name"]
				self.environment.add_sensor(environments.available_sensors[sensor["name"]](**sensor_arguments))
			except TypeError as e:
				raise VegvisirInvalidImplementationConfigurationException(f"Sensor [{sensor['name']}] can not be initialized with the provided arguments. Make sure all required initialization parameters are provided [f{e}]")
	
	# def _scan_image_repos(self):
	# 	self._image_sets = []
	# 	proc = subprocess.run(
	# 		"docker images | awk '(NR>1) {print $1, $2}'",
	# 		shell=True,
	# 		stdout=subprocess.PIPE,
	# 		stderr=subprocess.STDOUT
	# 	)
	# 	local_images = proc.stdout.decode('utf-8').strip().replace(' ', ':').split('\n')
	# 	for img in local_images:
	# 		repo = get_repo_from_image(img)
	# 		if repo in self._image_repos:
	# 			tag = get_tag_from_image(img)
	# 			set_name = get_name_from_image(img)
	# 			if not repo + '/' + set_name in self._image_sets:
	# 				self._image_sets.append(repo + '/' + set_name)
	# 			for x in self._clients + self._servers + self._shapers:
	# 				if hasattr(x, 'image_name') and x.image_name == tag:
	# 					x.images.append(Image(img))

	def _enable_ipv6(self):
		"""
		sudo modprobe ip6table_filter
		"""
		_, out, err = self.spawn_blocking_subprocess("modprobe ip6table_filter", True, False)
		# ipv6_proc = subprocess.Popen(
		# 		["sudo", "-S", "modprobe", "ip6table_filter"],
		# 		shell=False,
		# 		stdin=subprocess.PIPE,
		# 		stdout=subprocess.PIPE,
		# 		stderr=subprocess.STDOUT
		# 	)
		# out, err, _ = ipv6_proc.communicate(self._sudo_password.encode())
		if out != '' or err is not None:
			logging.debug("Vegvisir: enabling ipv6 resulted in non empty output: %s\n%s", out, err)

	def run(self) -> int:
		vegvisir_start_time = datetime.now()
		self._path_collection.log_path_date = os.path.join(self._path_collection.log_path_root, "{:%Y-%m-%dT_%H-%M-%S}".format(vegvisir_start_time))
		
		nr_failed = 0

		self._enable_ipv6()

		for shaper_config in self._shaper_configurations:
			for server_config in self._server_configurations:
				for client_config in self._client_configurations:
					logging.info(f'Running {client_config["name"]} over {shaper_config["name"]} against {server_config["name"]}')
					shaper = self._shapers[shaper_config["name"]]
					server = self._server_endpoints[server_config["name"]]
					client = self._client_endpoints[client_config["name"]]

					# SETUP
					if client.type == Endpoint.Type.HOST:
						_, out, err = self.spawn_blocking_subprocess("hostman add 193.167.100.100 server4", True, False)
						logging.debug("Vegvisir: append entry to hosts: %s", out.strip())
						if err is not None and len(err) > 0:
							logging.debug("Vegvisir: appending entry to hosts file resulted in error: %s", err)

					for run_number in range(0,self.iterations):
						# self._run_individual_test()
						start_time = datetime.now()
						
						# We want all output to be saved to file for later evaluation/debugging
						log_file = os.path.join(self._path_collection.log_path_permutation, "output.txt")
						log_handler = logging.FileHandler(log_file)
						log_handler.setLevel(logging.DEBUG)
						logging.getLogger().addHandler(log_handler)
			
						# Paths, we create the folders so we can later bind them as docker volumes for direct logging output
						# Avoids docker "no space left on device" errors
						self._path_collection.log_path_iteration = os.path.join(self._path_collection.log_path_date, f"run_{run_number}/") if self.iterations > 1 else self._path_collection.log_path_date
						self._path_collection.log_path_permutation = os.path.join(self._path_collection.log_path_iteration, f"{client_config.get('log_name', client_config['name'])}__{shaper_config.get('log_name', shaper_config['name'])}__{server_config.get('log_name', server_config['name'])}")
						self._path_collection.log_path_client = os.path.join(self._path_collection.log_path_permutation, 'client')
						self._path_collection.log_path_server = os.path.join(self._path_collection.log_path_permutation, 'server')
						self._path_collection.log_path_shaper = os.path.join(self._path_collection.log_path_permutation, 'shaper')
						for log_dir in [self._path_collection.log_path_client, self._path_collection.log_path_server, self._path_collection.log_path_shaper]:
							pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)
						pathlib.Path(os.path.join(self._path_collection.log_path_iteration, "client__shaper__server")).touch()

						# We want all output to be saved to file for later evaluation/debugging
						log_file = os.path.join(self._path_collection.log_path_permutation, "output.txt")
						log_handler = logging.FileHandler(log_file)
						log_handler.setLevel(logging.DEBUG)
						logging.getLogger().addHandler(log_handler)
						logging.info("Test output")
						logging.warning("Test warning")
						

						client_image = client.image.full if client.type == Endpoint.Type.DOCKER else "none"  # Docker compose v2 requires an image name, can't default to blank string

						cert_path = tempfile.TemporaryDirectory(dir="/tmp", prefix="vegvisir_certs_")
						self.environment.generate_cert_chain(cert_path.name)

						requests = client_config.get("REQUESTS", client_config.get("REQUEST_URLS", ""))

						# params = (
						# 	"WAITFORSERVER=server:443 "

						# 	"CLIENT=" + client_image + " "
						# 	"SERVER=" + server.name + " "
						# 	"SHAPER=" + shaper.name + " "
							
						# 	"TESTCASE_CLIENT=" + hardcoded_environment.QIR_compatability_testcase(Environment.Perspective.CLIENT) + " "
						# 	"REQUESTS=\"" + requests + "\"" + " "  # TODO jherbots better compatability check here

						# 	"DOWNLOADS=" + tempfile.TemporaryDirectory(dir="/tmp", prefix="vegvisir_downloads_").name + " "  # TODO rework this
						# 	"TESTCASE_SERVER=" + hardcoded_environment.QIR_compatability_testcase(Environment.Perspective.SERVER) + " "
						# 	"WWW=" + self.www_path + " "
						# 	"CERTS=" + cert_path.name + " "

						# 	"SCENARIO=" + shaper.scenarios[shaper_config["scenario"]].command + " "  # TODO parse this with args

						# 	"LOG_PATH_CLIENT=\"" + log_path_client + "\" "
						# 	"LOG_PATH_SERVER=\"" + log_path_shaper + "\" "
						# 	"LOG_PATH_SHAPER=\"" + log_path_server + "\" "
						# )
						# params = (

						# )

						docker_compose_vars = (
							"CLIENT=" + client_image + " "
							"SERVER=" + server.image.full + " "
							"SHAPER=" + shaper.image.full + " "

							"CERTS=" + cert_path.name + " "
							"WWW=" + self.www_path + " "
							"DOWNLOADS=" + tempfile.TemporaryDirectory(dir="/tmp", prefix="vegvisir_downloads_").name + " "  # TODO rework this

							"LOG_PATH_CLIENT=\"" + self._path_collection.log_path_client + "\" "
							"LOG_PATH_SERVER=\"" + self._path_collection.log_path_server + "\" "
							"LOG_PATH_SHAPER=\"" + self._path_collection.log_path_shaper + "\" "

							# "REQUESTS=https://server4/vegvisir_dummy.txt "
						)

						server_params = server.parameters.hydrate_with_arguments(server_config.get("arguments", {}), {"ROLE": "server", "SSLKEYLOGFILE": "/logs/keys.log", "QLOGDIR": "/logs/qlog/", "TESTCASE": self.environment.get_QIR_compatibility_testcase(BaseEnvironment.Perspective.SERVER)})
						# TODO serialize command
						shaper_params = shaper.scenarios[shaper_config["scenario"]].parameters.hydrate_with_arguments(shaper_config.get("arguments", {}), {"WAITFORSERVER": "server:443", "SCENARIO": shaper.scenarios[shaper_config["scenario"]].command})
						
						with open("server.env", "w") as fp:
							Parameters.serialize_to_env_file(server_params, fp)
						with open("shaper.env", "w") as fp:
							Parameters.serialize_to_env_file(shaper_params, fp)

						# params += " ".join(testcase.additional_envs())
						# params += " ".join(shaper.additional_envs())
						# params += " ".join(server.additional_envs())
						# containers = "sim server " + " ".join(testcase.additional_containers())
						containers = "sim server"

						cmd = (
							docker_compose_vars
							+ " docker compose up -d "
							+ containers
						)
						self.spawn_parallel_subprocess(cmd, False, True)

						# Host applications require some packet rerouting to be able to reach docker containers
						if self._client_endpoints[client_config["name"]].type == Endpoint.Type.HOST:
							_, out, err = self.spawn_blocking_subprocess("ip route del 193.167.100.0/24", True, False)
							logging.debug("Vegvisir: network setup: %s", out)
							if not err is None:
								logging.debug("Vegvisir: network error: %s", err)

							_, out, err = self.spawn_blocking_subprocess("ip route add 193.167.100.0/24 via 193.167.0.2", True, False)
							logging.debug("Vegvisir: network setup: %s", out)
							if not err is None:
								logging.debug("Vegvisir: network error: %s", err)

							_, out, err = self.spawn_blocking_subprocess("./veth-checksum.sh", True, False)
							logging.debug("Vegvisir: network setup: %s", out)
							if not err is None:
								logging.debug("Vegvisir: network error: %s", err)

						# Log kernel/net parameters
						_, out, err = self.spawn_blocking_subprocess("ip address", True, False)
						logging.debug("Vegvisir: net log:\n%s", out)
						if not err is None:
							logging.debug("Vegvisir: net log error: %s", err)

						_, out, err = self.spawn_blocking_subprocess("sysctl -a", True, False)
						logging.debug("Vegvisir: kernel log:\n%s", out)
						if not err is None:
							logging.debug("Vegvisir: kernel log error: %s", err)

						# Introduce small delay for server and shaper setup
						sleep(2)
						
						# Setup client
						client_params = client.parameters.hydrate_with_arguments(client_config.get("arguments", {}), {
							"ROLE": "client",
							"SSLKEYLOGFILE": "/logs/keys.log",
							"QLOGDIR": "/logs/qlog/",
							"TESTCASE": self.environment.get_QIR_compatibility_testcase(BaseEnvironment.Perspective.CLIENT),
							"LOG_PATH_CLIENT": self._path_collection.log_path_client,
							"LOG_PATH_SERVER": self._path_collection.log_path_server,
							"LOG_PATH_SHAPER": self._path_collection.log_path_shaper,
							"WAITFORSERVER": "server4:443",
							"CERT_FINGERPRINT": cert_fingerprint,
							"ORIGIN": "server4:443"
							})
						with open("client.env", "w") as fp:
							Parameters.serialize_to_env_file(client_params, fp)
						
						client_cmd = ""
						client_proc = None
						if client.type == Endpoint.Type.DOCKER:
							# params += " ".join(client.additional_envs())
							client_cmd = (
								docker_compose_vars
								+ " docker compose up --abort-on-container-exit --timeout 1 "
								+ "client"
							)
							client_proc = self.spawn_parallel_subprocess(client_cmd, False, True)

						elif client.type == Endpoint.Type.HOST:
							client_cmd = client.command.serialize_command(client_params)
							client_proc = self.spawn_parallel_subprocess(client_cmd)
						logging.debug("Vegvisir: running client: %s", client_cmd)

						try:
							self.environment.start_sensors(client_proc, self._path_collection)
							self.environment.waitfor_sensors()
							self.environment.clean_and_reset_sensors()
						except KeyboardInterrupt:
							self.environment.forcestop_sensors()
							self.environment.clean_and_reset_sensors()
							with open(os.path.join(self._path_collection.log_path_permutation, "crashreport.txt"), "w") as fp:
								fp.write("Test aborted by user interaction.")
							logging.info("CTRL-C test interrupted")

						out, err = client_proc.communicate()
						logging.debug(out.decode("utf-8"))
						logging.debug(err.decode("utf-8"))
						client_proc.terminate()
						# proc = subprocess.run(
						# 	docker_compose_vars + " docker compose logs --timestamps",
						# 	shell=True,
						# 	stdout=subprocess.PIPE,
						# 	stderr=subprocess.STDOUT
						# )
						_, out, err = self.spawn_blocking_subprocess(docker_compose_vars + " docker compose logs --timestamps", False, True)
						logging.debug(out)
						logging.debug(err)

						_, out ,err = self.spawn_blocking_subprocess(docker_compose_vars + " docker compose down", False, True) # TODO TEMP
						logging.debug(out)

					# BREAKDOWN
					if client.type == Endpoint.Type.HOST:
						_, out, err = self.spawn_blocking_subprocess("hostman remove --names=server4")
						logging.debug("Vegvisir: remove entry from hosts: %s", out.decode('utf-8').strip())
						if err is not None and len(err) > 0:
							logging.debug("Vegvisir: removing entry from hosts file resulted in error: %s", err)


					# TODO PLACE CORRECTLY
					logging.getLogger().removeHandler(log_handler)
					log_handler.close()  # TODO jherbots clean this and replace with nicer handler

		# self._clients_active = list((x for x in list(self._clients.values()) if x.active))
		# self._servers_active = list((x for x in list(self._servers.values()) if x.active))
		# self._shapers_active = list((x for x in list(self._shapers.values()) if x.active))
		# self._tests_active = list((x for x in self._tests if x.active))

		# for x in self._shapers_active + self._servers_active + self._shapers_active:
		# 	x.status = RunStatus.WAITING
		# 	if hasattr(x, 'scenarios'):
		# 		for y in x.scenarios:
		# 			y.status = RunStatus.WAITING
		# print(self._clients_active)
		# print(self._servers_active)
		# print(self._shapers_active)

	# 	for shaper in self._shapers_active:
	# 		shaper.status = RunStatus.RUNNING
	# 		for scenario in list((x for x in shaper.scenarios if x.active)):
	# 			scenario.status = RunStatus.RUNNING
	# 			shaper_images = list((x for x in shaper.images if x.active))
	# 			for shaper_image in shaper_images:
	# 				shaper.curr_image = shaper_image
	# 				for server in self._servers_active:
	# 					server.status = RunStatus.RUNNING
	# 					server_images = list((x for x in server.images if x.active))
	# 					for server_image in server_images:
	# 						server.curr_image = server_image
	# 						for client in self._clients_active:
	# 							client.status = RunStatus.RUNNING

	# 							if client.type == Type.APPLICATION:
	# 								#TODO create backup using -b and reset to backup instead of removing entry later
	# 								hosts_proc = subprocess.Popen(
	# 										["sudo", "-S", "hostman", "add", "193.167.100.100", "server4"],
	# 										shell=False,
	# 										stdin=subprocess.PIPE,
	# 										stdout=subprocess.PIPE,
	# 										stderr=subprocess.STDOUT
	# 									)
	# 								out, err, _ = hosts_proc.communicate(self._sudo_password.encode())
	# 								logging.debug("Vegvisir: append entry to hosts: %s", out.decode('utf-8'))
	# 								if not err is None:
	# 									logging.debug("Vegvisir: appending entry to hosts file resulted in error: %s", err)

	# 							for test in self._tests_active:
	# 								test.status = RunStatus.RUNNING

	# 								testcase = test.testcase
	# 								testcase.scenario = scenario

	# 								if client.type == Type.DOCKER:
	# 									client_images = list((x for x in client.images if x.active))
	# 									for client_image in client_images:
	# 										client.curr_image = client_image
	# 										logging.debug("Vegvisir: running with shaper %s (%s) (scenario: %s), server %s (%s), and client %s (%s)",
	# 										shaper.name, shaper_image.url, scenario.arguments,
	# 										server.name, server_image.url,
	# 										client.name, client_image.url
	# 										)

	# 										self._curr_repetition = 1
	# 										for _ in range(self._test_repetitions):
	# 											result = self._run_test(shaper, server, client, testcase)
	# 											logging.debug("Vegvisir: \telapsed time since start of test: %s", str(result.end_time - result.start_time))
	# 											self._curr_repetition += 1
										
	# 								else:
	# 									logging.debug("Vegvisir: running with shaper %s (%s) (scenario: %s), server %s (%s), and client %s",
	# 									shaper.name, shaper_image.url, scenario.arguments,
	# 									server.name, server_image.url,
	# 									client.name
	# 									)

	# 									self._curr_repetition = 1
	# 									for _ in range(self._test_repetitions):
	# 										result = self._run_test(shaper, server, client, testcase)
	# 										logging.debug("Vegvisir: \telapsed time since start of test: %s", str(result.end_time - result.start_time))
	# 										self._curr_repetition += 1
	# 								test.status = RunStatus.DONE
	# 							client.status = RunStatus.DONE

	# 							if client.type == Type.APPLICATION:
	# 								hosts_proc = subprocess.Popen(
	# 										["sudo", "-S", "hostman", "remove", "--names=server4"],
	# 										shell=False,
	# 										stdin=subprocess.PIPE,
	# 										stdout=subprocess.PIPE,
	# 										stderr=subprocess.STDOUT
	# 									)
	# 								out, err, _ = hosts_proc.communicate(self._sudo_password.encode())
	# 								logging.debug("Vegvisir: remove entry from hosts: %s", out.decode('utf-8'))
	# 								if not err is None:
	# 									logging.debug("Vegvisir: removing entry from hosts file resulted in error: %s", err)
	# 					server.status = RunStatus.DONE
	# 			scenario.status = RunStatus.DONE
	# 		shaper.status = RunStatus.DONE

	# 	self._end_time = datetime.now()
	# 	logging.info("elapsed time since start of run: %s", str(self._end_time - self._start_time))
	# 	self._running = False
	# 	return nr_failed

	# def _run_test(
	# 	self,
	# 	shaper: Implementation,
	# 	server: Implementation, 
	# 	client: Implementation,
	# 	testcase: TestCase
	# 	) -> TestResult:
	# 	result = TestResult()
	# 	result.start_time = datetime.now()

	# 	sim_log_dir = tempfile.TemporaryDirectory(dir="/tmp", prefix="logs_sim_")
	# 	server_log_dir = tempfile.TemporaryDirectory(dir="/tmp", prefix="logs_server_")
	# 	client_log_dir = tempfile.TemporaryDirectory(dir="/tmp", prefix="logs_client_")
	# 	log_file = tempfile.NamedTemporaryFile(dir="/tmp", prefix="output_log_")
	# 	log_handler = logging.FileHandler(log_file.name)
	# 	log_handler.setLevel(logging.DEBUG)

	# 	log_dir = os.getcwd() + "/" + self._log_dir + "/"
	# 	log_dir = log_dir + server.curr_image.repo + "_" + server.curr_image.name + "_" + server.curr_image.tag + "_"
	# 	if client.type == Type.DOCKER:
	# 		log_dir = log_dir + client.curr_image.repo + "_" + client.curr_image.name + "_" + client.curr_image.tag
	# 	else:
	# 		log_dir = log_dir + client.name 
	# 	log_dir = log_dir + "/" + shaper.curr_image.name + "_" + testcase.scenario.name + "/" + testcase.name
	# 	if self._test_repetitions > 1:
	# 		log_dir += '_run_' + str(self._curr_repetition)

	# 	client_log_dir_local = log_dir + '/client'
	# 	server_log_dir_local = log_dir + '/server'
	# 	shaper_log_dir_local = log_dir + '/shaper'
	# 	pathlib.Path(client_log_dir_local).mkdir(parents=True, exist_ok=True)
	# 	pathlib.Path(server_log_dir_local).mkdir(parents=True, exist_ok=True)
	# 	pathlib.Path(shaper_log_dir_local).mkdir(parents=True, exist_ok=True)

	# 	print(client_log_dir_local)

	# 	formatter = LogFileFormatter("%(asctime)s %(message)s")
	# 	log_handler.setFormatter(formatter)
	# 	logging.getLogger().addHandler(log_handler)

	# 	client_image = "none"
	# 	if hasattr(client,"curr_image"):
	# 		client_image = client.curr_image.url

	# 	params = (
	# 		"WAITFORSERVER=server:443 "

	# 		#"CLIENT=" + client.image + " "
	# 		"TESTCASE_CLIENT=" + testcase.testname(Perspective.CLIENT) + " "
	# 		"REQUESTS=\"" + testcase.request_urls + "\"" + " "

	# 		"DOWNLOADS=" + testcase.download_dir() + " "
	# 		"SERVER=" + server.curr_image.url + " "
	# 		"TESTCASE_SERVER=" + testcase.testname(Perspective.SERVER) + " "
	# 		"WWW=" + testcase.www_dir() + " "
	# 		"CERTS=" + testcase.certs_dir() + " "

	# 		"SHAPER=" + shaper.curr_image.url + " "
	# 		"SCENARIO=" + testcase.scenario.arguments + " "

	# 		"SERVER_LOGS=" + "/logs" + " "
	# 		"CLIENT_LOGS=" + "/logs" + " "

	# 		"CLIENT=" + client_image + " "	# required for compose v2

	# 		"CLIENT_LOG_DIR=\"" + client_log_dir_local + "\" "
	# 		"SERVER_LOG_DIR=\"" + server_log_dir_local + "\" "
	# 		"SHAPER_LOG_DIR=\"" + shaper_log_dir_local + "\" "
	# 	)
	# 	params += " ".join(testcase.additional_envs())
	# 	params += " ".join(shaper.additional_envs())
	# 	params += " ".join(server.additional_envs())
	# 	containers = "sim server " + " ".join(testcase.additional_containers())

	# 	cmd = (
	# 		params
	# 		+ " docker-compose up -d "
	# 		+ containers
	# 	)

	# 	result.status = Status.FAILED
	# 	try:
	# 		# Setup client
	# 		if client.type == Type.APPLICATION:
	# 			for setup_cmd in client.setup:
	# 				out = ""
	# 				setup_cmd.command_formatted = setup_cmd.command.format(client_log_dir=client_log_dir_local, server_log_dir=server_log_dir_local, shaper_log_dir=shaper_log_dir_local)
	# 				logging.debug("Vegvisir: setup command: %s", setup_cmd.command_formatted)
	# 				if setup_cmd.replace_tilde:
	# 					setup_cmd.command_formatted = setup_cmd.command_formatted.replace("~", str(Path.home()))
	# 				if setup_cmd.sudo:
	# 					net_proc = subprocess.Popen(
	# 					["sudo", "-S"] + setup_cmd.command_formatted.split(" "),
	# 					shell=False,
	# 					stdin=subprocess.PIPE,
	# 					stdout=subprocess.PIPE,
	# 					stderr=subprocess.STDOUT
	# 				)
	# 					o, e = net_proc.communicate(self._sudo_password.encode())
	# 					out += str(o) + "\n" + str(e)
	# 				else:
	# 					proc = subprocess.run(
	# 						setup_cmd.command_formatted,
	# 						shell=True,
	# 						stdout=subprocess.PIPE,
	# 						stderr=subprocess.STDOUT
	# 					)
	# 					out += proc.stdout.decode("utf-8")
	# 				logging.debug("Vegvisir: client setup: %s\n%s", setup_cmd.command_formatted, out)

	# 		# Setup server and network
	# 		#TODO exit on error
	# 		logging.debug("Vegvisir: running command: %s", cmd)
	# 		proc = subprocess.run(
	# 			cmd,
	# 			shell=True,
	# 			stdout=subprocess.PIPE,
	# 			stderr=subprocess.STDOUT
	# 		)
			
	# 		if client.type == Type.APPLICATION:
	# 			net_proc = subprocess.Popen(
	# 				["sudo", "-S", "ip", "route", "del", "193.167.100.0/24"],
	# 				shell=False,
	# 				stdin=subprocess.PIPE,
	# 				stdout=subprocess.PIPE,
	# 				stderr=subprocess.STDOUT
	# 			)
	# 			out, err, _ = net_proc.communicate(self._sudo_password.encode())
	# 			logging.debug("Vegvisir: network setup: %s", out.decode("utf-8"))
	# 			if not err is None:
	# 				logging.debug("Vegvisir: network error: %s", err.decode("utf-8"))
	# 			net_proc = subprocess.Popen(
	# 				["sudo", "-S", "ip", "route", "add", "193.167.100.0/24", "via", "193.167.0.2"],
	# 				shell=False,
	# 				stdin=subprocess.PIPE,
	# 				stdout=subprocess.PIPE,
	# 				stderr=subprocess.STDOUT
	# 			)
	# 			out, err, _ = net_proc.communicate(self._sudo_password.encode())
	# 			logging.debug("Vegvisir: network setup: %s", out.decode("utf-8"))
	# 			if not err is None:
	# 				logging.debug("Vegvisir: network error: %s", err.decode("utf-8"))
	# 			net_proc = subprocess.Popen(
	# 				["sudo", "-S", "./veth-checksum.sh"],
	# 				shell=False,
	# 				stdin=subprocess.PIPE,
	# 				stdout=subprocess.PIPE,
	# 				stderr=subprocess.STDOUT
	# 			)
	# 			out, err, _ = net_proc.communicate(self._sudo_password.encode())
	# 			logging.debug("Vegvisir: network setup: %s", out.decode("utf-8"))
	# 			if not err is None:
	# 				logging.debug("Vegvisir: network error: %s", err.decode("utf-8"))

	# 		# Log kernel/net parameters
	# 		net_proc = subprocess.Popen(
	# 			["sudo", "-S", "ip", "a"],
	# 			shell=False,
	# 			stdin=subprocess.PIPE,
	# 			stdout=subprocess.PIPE,
	# 			stderr=subprocess.STDOUT
	# 		)
	# 		out, err, _ = net_proc.communicate(self._sudo_password.encode())
	# 		logging.debug("Vegvisir: net log:\n%s", out.decode("utf-8"))
	# 		if not err is None:
	# 			logging.debug("Vegvisir: net log error: %s", err.decode("utf-8"))

	# 		kernel_proc = subprocess.Popen(
	# 			["sudo", "-S", "sysctl", "-a"],
	# 			shell=False,
	# 			stdin=subprocess.PIPE,
	# 			stdout=subprocess.PIPE,
	# 			stderr=subprocess.STDOUT
	# 		)
	# 		out, err, _ = kernel_proc.communicate(self._sudo_password.encode())
	# 		logging.debug("Vegvisir: kernel log:\n%s", out.decode("utf-8"))
	# 		if not err is None:
	# 			logging.debug("Vegvisir: kernel log error: %s", err.decode("utf-8"))

	# 		# Wait for server and shaper to be ready
	# 		sleep(2)
			
	# 		# Setup client
	# 		client_cmd = ""
	# 		client_proc = None
	# 		if client.type == Type.DOCKER:
	# 			params += " ".join(client.additional_envs())
	# 			client_cmd = (
	# 				params
	# 				+ " docker-compose up --abort-on-container-exit --timeout 1 "
	# 				+ "client"
	# 			)
	# 			client_proc = subprocess.Popen(
	# 				client_cmd,
	# 				shell=True,
	# 				stdout=subprocess.PIPE,
	# 				stderr=subprocess.STDOUT
	# 			)

	# 		elif client.type == Type.APPLICATION:
	# 			client_cmd = client.command.format(origin=testcase.origin, cert_fingerprint=testcase.cert_fingerprint, request_urls=testcase.request_urls, client_log_dir=client_log_dir_local, server_log_dir=server_log_dir_local, shaper_log_dir=shaper_log_dir_local)
	# 			logging.debug("Vegvisir: running client: %s", client_cmd)
	# 			client_proc = subprocess.Popen(
	# 				client_cmd.split(' '),
	# 				shell=False,
	# 				stdout=subprocess.PIPE,
	# 				stderr=subprocess.STDOUT,
	# 			)
	# 		logging.debug("Vegvisir: running client: %s", client_cmd)

	# 		try:
	# 			if isinstance(testcase.testend, TestEndUntilDownload):
	# 				testcase.testend.setup(client_proc, log_dir + '/client', testcase.file_to_find, testcase.timeout_time)
	# 			elif isinstance(testcase.testend, TestEndTimeout):
	# 				testcase.testend.setup(client_proc, testcase.timeout_time)
	# 			else:
	# 				testcase.testend.setup(client_proc)
	# 			testcase.testend.wait_for_end()
	# 		except KeyboardInterrupt as e:
	# 			logging.debug("Vegvisir: manual interrupt")
	# 		# Wait for tests
	# 		# try:
	# 		# 	#TODO use threading instead? wait for events? how to do infinite sleep?
	# 		# 	time.sleep(testcase.timeout) #TODO get from testcase
	# 		# 	raise subprocess.TimeoutExpired(cmd, testcase.timeout, proc.stdout, proc.stderr)
	# 		# except KeyboardInterrupt as e:
	# 		# 	logging.debug("Vegvisir: manual interrupt")
	# 		client_proc_stdout, _ = client_proc.communicate()
	# 		if client_proc_stdout != None:
	# 			logging.debug("Vegvisir: client: %s", client_proc_stdout.decode("utf-8"))
	# 		logging.debug("Vegvisir: proc: %s", proc.stdout.decode("utf-8"))
	# 		proc = subprocess.run(
	# 			params + " docker-compose logs -t",
	# 			shell=True,
	# 			stdout=subprocess.PIPE,
	# 			stderr=subprocess.STDOUT
	# 		)
	# 		logging.debug("Vegvisir: %s", proc.stdout.decode("utf-8"))
	# 		result.status = Status.SUCCES
	# 	except subprocess.TimeoutExpired as e:
	# 		logging.debug("Vegvisir: subprocess timeout: %s", e.stdout.decode("utf-8"))
	# 	except Exception as e:
	# 		logging.debug("Vegvisir: subprocess error: %s", str(e))

	# 	# self._copy_logs("sim", sim_log_dir, params)
	# 	# if client.type == Type.DOCKER:
	# 		# self._copy_logs("client", client_log_dir, params)
	# 	# self._copy_logs("server", server_log_dir, params)

	# 	# save logs
	# 	logging.getLogger().removeHandler(log_handler)
	# 	log_handler.close()
	# 	if result.status == Status.FAILED or result.status == Status.SUCCES:
	# 		# shutil.copytree(server_log_dir.name, server_log_dir_local, dirs_exist_ok=True)
	# 		# shutil.copytree(client_log_dir.name, client_log_dir_local, dirs_exist_ok=True)
	# 		# shutil.copytree(sim_log_dir.name, shaper_log_dir_local, dirs_exist_ok=True)
	# 		shutil.copyfile(log_file.name, log_dir + "/output.txt")
	# 		if self._save_files: #and result.status == Status.FAILED:
	# 			#shutil.copytree(testcase.www_dir(), log_dir + "/www", dirs_exist_ok=True)
	# 			try:
	# 				shutil.copytree(testcase.download_dir(), log_dir + "/downloads", dirs_exist_ok=True)
	# 			except Exception as exception:
	# 				logging.info("Could not copy downloaded files: %s", exception)

	# 	server_log_dir.cleanup()
	# 	client_log_dir.cleanup()
	# 	sim_log_dir.cleanup()

	# 	try:
	# 		logging.debug("Vegvisir: shutting down containers")
	# 		proc = subprocess.run(
	# 			params + " docker-compose down",
	# 			shell=True,
	# 			stdout=subprocess.PIPE,
	# 			stderr=subprocess.STDOUT
	# 		)
	# 		logging.debug("Vegvisir: shut down successful: %s", proc.stdout.decode("utf-8"))
	# 	except Exception as e:
	# 		logging.debug("Vegvisir: subprocess error while shutting down: %s", str(e))

	# 	result.end_time = datetime.now()
	# 	return result


	def _copy_logs(self, container: str, dir: tempfile.TemporaryDirectory, params: str):
		r = subprocess.run(
			'docker cp "$('
			+ params + " "
			+ 'docker-compose --log-level ERROR ps -q '
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

	## Docker
	def docker_update_images(self) -> int:
		r = subprocess.run(
			"docker images | grep -v ^REPO | sed 's/ \+/:/g' | cut -d: -f1,2 | xargs -L1 docker pull",
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
		)
		if r.returncode != 0:
			logging.info(
				"Updating docker images failed: %s", r.stdout.decode("utf-8")
			)
		return r.returncode

	def docker_save_imageset(self, imageset) -> int:
		r = subprocess.run(
			"docker save -o {} {}".format(imageset.replace('/', '_') + ".tar", imageset),
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
		)
		if r.returncode != 0:
			logging.info(
				"Saving docker images failed: %s", r.stdout.decode("utf-8")
			)
		return r.returncode

	def docker_load_imageset(self, imageset_tar) -> int:
		r = subprocess.run(
			"docker load -i {}".format(imageset_tar),
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
		)
		if r.returncode != 0:
			logging.info(
				"Loading docker images failed: %s", r.stdout.decode("utf-8")
			)
		return r.returncode

	def docker_create_imageset(self, repo, setname) -> int:
		returncode = 0
		for x in self._clients + self._servers + self._shapers:
			if hasattr(x, "images"):
				img = x.images[0]
				r = subprocess.run(
					"docker tag {} {}".format(img.url, repo + "/" + setname + ":" + img.name),
					shell=True,
					stdout=subprocess.PIPE,
					stderr=subprocess.STDOUT,
				)
				if r.returncode != 0:
					logging.info(
						"Tagging docker image %s failed: %s", img.url, r.stdout.decode("utf-8")
					)
				returncode += r.returncode
		return returncode
	
	def docker_pull_source_images(self) -> int:
		returncode = 0
		for x in self._clients + self._servers + self._shapers:
			if hasattr(x, "images"):
				img = x.images[0]
				r = subprocess.run(
					"docker pull {}".format(img.url),
					shell=True,
					stdout=subprocess.PIPE,
					stderr=subprocess.STDOUT,
				)
				if r.returncode != 0:
					logging.info(
						"Pulling docker image %s failed: %s", img.url, r.stdout.decode("utf-8")
					)
				returncode += r.returncode
		return returncode

	def docker_remove_imageset(self, imageset) -> int:
		r = subprocess.run(
			"docker images | grep {} | grep -v ^REPO | sed 's/ \+/:/g' | cut -d: -f1,2 | xargs -L1 docker image rm".format(imageset),
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
		)
		if r.returncode != 0:
			logging.info(
				"Removing docker imageset {} failed: %s", imageset, r.stdout.decode("utf-8")
			)
		return r.returncode