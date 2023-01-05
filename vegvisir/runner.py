import dataclasses
from datetime import datetime
import getpass
import grp
import logging
import os
import pathlib
import queue
import shlex
import sys
import subprocess
import threading
import time
from typing import Dict, List, Set, Tuple
import json
import tempfile
import re
import shutil
from vegvisir import environments
from vegvisir.data import ExperimentPaths, VegvisirArguments
from vegvisir.environments.base_environment import BaseEnvironment

from .implementation import DockerImage, Parameters, HostCommand, Endpoint, Scenario, Shaper, VegvisirArgumentException, VegvisirCommandException

class VegvisirException(Exception):
	pass

class VegvisirInvalidImplementationConfigurationException(Exception):
	pass

class VegvisirInvalidExperimentConfigurationException(Exception):
	pass

class VegvisirCommandExecutionException(Exception):
	pass

class VegvisirRunFailedException(Exception):
	pass

class LogFileFormatter(logging.Formatter):
	def format(self, record):
		msg = super(LogFileFormatter, self).format(record)
		# remove color control characters
		return re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]").sub("", msg)

class Runner:
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
		self.hook_processor_count = 4
		self.hook_processors: List[threading.Thread] = []
		self.hook_processor_request_stop: bool = False
		self.hook_processor_queue: queue.Queue = queue.Queue()  # contains tuples (method pointer, path dataclass)

		self._sudo_password = sudo_password
		self._debug = debug

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
		return proc, out.decode("utf-8").strip(), err.decode("utf-8").strip()

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
				def _load_and_dryrun_setup_command(setup_type: str, collection: List[HostCommand]):
					if setup_type not in configuration:
						return
					if implementation_type == Endpoint.Type.DOCKER:
						raise VegvisirInvalidImplementationConfigurationException(f"Client [{client}] represents a containerized configuration, these can not contain a '{setup_type}' key.")
					for index, task in enumerate(configuration[setup_type]):
						if "command" not in task:
							raise VegvisirInvalidImplementationConfigurationException(f"{setup_type.capitalize()} task #{index} of client [{client}] does not contain the 'command' entry.")
						setup_command = HostCommand(task["command"], task.get("root_required", False))
						try:
							setup_command.serialize_command(parameters.hydrate_with_empty_arguments())
						except VegvisirCommandException as e:
							raise VegvisirInvalidImplementationConfigurationException(f"Client [{client}] {setup_type} command [{setup_command.command}] contains unknown parameters, dry run failed => {e}")
						collection.append(setup_command)
				_load_and_dryrun_setup_command("construct", impl.construct)
				_load_and_dryrun_setup_command("destruct", impl.destruct)
			
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

	def load_experiment_from_file(self, file_path: str) -> None:
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

		vegvisirDummyArguments = VegvisirArguments().dummy()
		def _validate_command_with_real_parameters(client_endpoint: Endpoint, client_unhydrated_parameters: Dict[str, str]) -> None:
			if client_endpoint.type == Endpoint.Type.DOCKER:
				return

			try:
				commands = [client_endpoint.command] + client_endpoint.construct + client_endpoint.destruct
				hydrated_parameters = client_endpoint.parameters.hydrate_with_arguments(client_unhydrated_parameters, vegvisirDummyArguments)
				print(hydrated_parameters)
				for cmd in commands:
					cmd.serialize_command(hydrated_parameters)
			except VegvisirArgumentException as e:
				raise VegvisirInvalidExperimentConfigurationException(f"Client [{client_endpoint.name}] contains a command [{cmd.command}] that fails to serialize: {e}")
		
		duplicate_check = set()
		for index, client in enumerate(configuration[CLIENTS_KEY]):
			_namecheck_dict(client, index, "client", self._client_endpoints)
			_duplicate_check(client["name"], client.get("log_name"), duplicate_check, "client")
			duplicate_check.add(client["log_name"] if client.get("log_name") is not None else client["name"])
			_parametercheck_endpoint(self._client_endpoints[client["name"]], client, "client")
			_validate_command_with_real_parameters(self._client_endpoints[client["name"]], client.get("arguments", {}))
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

		hook_processors = settings.get("hook_processors", 4)
		if type(hook_processors) is str and not hook_processors.isdigit():
			raise VegvisirInvalidExperimentConfigurationException("Setting 'hook_processors' must be > 0.")
		try:
			self.hook_processor_count = int(hook_processors)
		except ValueError:
			raise VegvisirInvalidExperimentConfigurationException("Setting 'hook_processors' must be > 0.")
		if self.hook_processor_count <= 0:
			raise VegvisirInvalidExperimentConfigurationException("Setting 'hook_processors' must be > 0.")

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

	def _hook_processor(self):
		while not self.hook_processor_request_stop:
			try:
				task, experiment_paths = self.hook_processor_queue.get(timeout=5)
				task(experiment_paths)
			except queue.Empty:
				pass  # We can ignore this one


	def _enable_ipv6(self):
		"""
		sudo modprobe ip6table_filter
		"""
		_, out, err = self.spawn_blocking_subprocess("modprobe ip6table_filter", True, False)
		if out != '' or err is not None:
			logging.debug("Vegvisir: enabling ipv6 resulted in non empty output: %s\n%s", out, err)

	def print_debug_information(self, command: str) -> None:
		_, out, err = self.spawn_blocking_subprocess(command, True, False)
		logging.debug(f"Command [{command}]:\n{out}")
		if err is not None and len(err) > 0:
			logging.warning(f"Command [{command}] returned stderr output:\n{err}")

	def run(self):
		vegvisir_start_time = datetime.now()

		# Root path for logs needs to be known and exist for metadata copies
		self._path_collection.log_path_date = os.path.join(self._path_collection.log_path_root, "{:%Y-%m-%dT_%H-%M-%S}".format(vegvisir_start_time))
		pathlib.Path(self._path_collection.log_path_date).mkdir(parents=True, exist_ok=True)
		
		# Copy the implementations and experiment configurations for reproducibility purposes
		# For now, assume json files
		implementations_destination = os.path.join(self._path_collection.log_path_date, "implementations.json")
		experiment_destination = os.path.join(self._path_collection.log_path_date, "experiment.json")
		try:
			shutil.copy2(self._path_collection.implementations_configuration_file_path, implementations_destination) 
		except IOError as e:
			logging.warning(f"Could not copy over implementations configuration to root of experiment logs: {implementations_destination} | {e}")
		try:
			shutil.copy2(self._path_collection.experiment_configuration_file_path, experiment_destination) 
		except IOError as e:
			logging.warning(f"Could not copy over experiment configuration to root of experiment logs: {experiment_destination} | {e}")

		for _ in range(max(1, self.hook_processor_count)):
			processor = threading.Thread(target=self._hook_processor)
			processor.start()
			self.hook_processors.append(processor)

		self._enable_ipv6()

		experiment_permutation_total = len(self._shaper_configurations) * len(self._server_configurations) * len(self._client_configurations) * self.iterations
		experiment_permutation_counter = 0
		for shaper_config in self._shaper_configurations:
			for server_config in self._server_configurations:
				for client_config in self._client_configurations:
					yield client_config["name"], shaper_config["name"], server_config["name"], experiment_permutation_counter, experiment_permutation_total
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
						
						# Paths, we create the folders so we can later bind them as docker volumes for direct logging output
						# Avoids docker "no space left on device" errors
						self._path_collection.log_path_iteration = os.path.join(self._path_collection.log_path_date, f"run_{run_number}/") if self.iterations > 1 else self._path_collection.log_path_date
						self._path_collection.log_path_permutation = os.path.join(self._path_collection.log_path_iteration, f"{client_config.get('log_name', client_config['name'])}__{shaper_config.get('log_name', shaper_config['name'])}__{server_config.get('log_name', server_config['name'])}")
						self._path_collection.log_path_client = os.path.join(self._path_collection.log_path_permutation, 'client')
						self._path_collection.log_path_server = os.path.join(self._path_collection.log_path_permutation, 'server')
						self._path_collection.log_path_shaper = os.path.join(self._path_collection.log_path_permutation, 'shaper')
						self._path_collection.download_path_client = os.path.join(self._path_collection.log_path_permutation, 'downloads')
						for log_dir in [self._path_collection.log_path_client, self._path_collection.log_path_server, self._path_collection.log_path_shaper, self._path_collection.download_path_client]:
							pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)
						pathlib.Path(os.path.join(self._path_collection.log_path_iteration, "client__shaper__server")).touch()						

						# We want all output to be saved to file for later evaluation/debugging
						log_file = os.path.join(self._path_collection.log_path_permutation, "output.txt")
						log_handler = logging.FileHandler(log_file)
						log_handler.setLevel(logging.DEBUG)
						logging.getLogger().addHandler(log_handler)

						path_collection_copy = dataclasses.replace(self._path_collection)
						self.hook_processor_queue.put((self.environment.pre_run_hook, path_collection_copy))  # Queue is infinite, should not block

						vegvisirBaseArguments = VegvisirArguments()
						vegvisirBaseArguments.LOG_PATH_CLIENT = self._path_collection.log_path_client
						vegvisirBaseArguments.LOG_PATH_SERVER = self._path_collection.log_path_server
						vegvisirBaseArguments.LOG_PATH_SHAPER = self._path_collection.log_path_shaper
						vegvisirBaseArguments.DOWNLOAD_PATH_CLIENT = self._path_collection.download_path_client

						client_image = client.image.full if client.type == Endpoint.Type.DOCKER else "none"  # Docker compose v2 requires an image name, can't default to blank string

						cert_path = tempfile.TemporaryDirectory(dir="/tmp", prefix="vegvisir_certs_")
						vegvisirBaseArguments.CERT_FINGERPRINT = self.environment.generate_cert_chain(cert_path.name)

						# TODO pick a better/cleaner spot to do this
						vegvisirBaseArguments.ORIGIN = "server4"
						vegvisirBaseArguments.ORIGIN_IPV4 = "server4"
						vegvisirBaseArguments.ORIGIN_IPV6 = "server6" # TODO hostman this
						vegvisirBaseArguments.ORIGIN_PORT = "443"
						vegvisirBaseArguments.WAITFORSERVER = "server4:443"
						vegvisirBaseArguments.SSLKEYLOGFILE = "/logs/keys.log"
						vegvisirBaseArguments.QLOGDIR = "/logs/qlog/"
						vegvisirBaseArguments.SCENARIO = shaper.scenarios[shaper_config["scenario"]].command

						vegvisirServerArguments = dataclasses.replace(vegvisirBaseArguments, ROLE="server", TESTCASE=self.environment.get_QIR_compatibility_testcase(BaseEnvironment.Perspective.SERVER))
						vegvisirShaperArguments = dataclasses.replace(vegvisirBaseArguments, ROLE="shaper", WAITFORSERVER="server:443")  # Important: Shaper uses server instead of server4

						docker_compose_vars = (
							"CLIENT=" + client_image + " "
							"SERVER=" + server.image.full + " "
							"SHAPER=" + shaper.image.full + " "

							"CERTS=" + cert_path.name + " "
							"WWW=" + self.www_path + " "
							"DOWNLOAD_PATH_CLIENT=\"" + self._path_collection.download_path_client + "\" "

							"LOG_PATH_CLIENT=\"" + self._path_collection.log_path_client + "\" "
							"LOG_PATH_SERVER=\"" + self._path_collection.log_path_server + "\" "
							"LOG_PATH_SHAPER=\"" + self._path_collection.log_path_shaper + "\" "
						)

						
						# server_params = server.parameters.hydrate_with_arguments(server_config.get("arguments", {}), {"ROLE": "server", "SSLKEYLOGFILE": "/logs/keys.log", "QLOGDIR": "/logs/qlog/", "TESTCASE": self.environment.get_QIR_compatibility_testcase(BaseEnvironment.Perspective.SERVER)})
						server_params = server.parameters.hydrate_with_arguments(server_config.get("arguments", {}), vegvisirServerArguments.dict())
						# shaper_params = shaper.scenarios[shaper_config["scenario"]].parameters.hydrate_with_arguments(shaper_config.get("arguments", {}), {"WAITFORSERVER": "server:443", "SCENARIO": shaper.scenarios[shaper_config["scenario"]].command})
						shaper_params = shaper.scenarios[shaper_config["scenario"]].parameters.hydrate_with_arguments(shaper_config.get("arguments", {}), vegvisirShaperArguments.dict())
						
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
						# self.spawn_parallel_subprocess(cmd, False, True)
						self.spawn_blocking_subprocess(cmd, False, True) # TODO Test out if this truly fixes the RNETLINK error? This call might be too slow
						
						# Host applications require some packet rerouting to be able to reach docker containers
						if self._client_endpoints[client_config["name"]].type == Endpoint.Type.HOST:
							logging.debug("Detected local client, rerouting localhost traffic to 193.167.100.0/24 via 193.167.0.2")
							_, out, err = self.spawn_blocking_subprocess("ip route del 193.167.100.0/24", True, False)
							if err is not None and len(err) > 0:
								raise VegvisirRunFailedException(f"Failed to remove route to 193.167.100.0/24 | STDOUT [{out}] | STDERR [{err}]")
							logging.debug("Removed docker compose route to 193.167.100.0/24")

							_, out, err = self.spawn_blocking_subprocess("ip route add 193.167.100.0/24 via 193.167.0.2", True, False)
							if err is not None and len(err) > 0:
								raise VegvisirRunFailedException(f"Failed to reroute 193.167.100.0/24 via 193.167.0.2 | STDOUT [{out}] | STDERR [{err}]")
							logging.debug("Rerouted 193.167.100.0/24 via 193.167.0.2")

							_, out, err = self.spawn_blocking_subprocess("./veth-checksum.sh", True, False)
							if err is not None and len(err) > 0:
								raise VegvisirRunFailedException(f"Virtual ethernet device checksum failed | STDOUT [{out}] | STDERR [{err}]")								

						# Log kernel/net parameters
						self.print_debug_information("ip address")
						self.print_debug_information("ip route list")
						self.print_debug_information("sysctl -a")
						self.print_debug_information("docker version")
						self.print_debug_information("docker compose version")

						# Setup client
						vegvisirClientArguments = dataclasses.replace(vegvisirBaseArguments, ROLE = "client", TESTCASE = self.environment.get_QIR_compatibility_testcase(BaseEnvironment.Perspective.CLIENT))
						client_params = client.parameters.hydrate_with_arguments(client_config.get("arguments", {}), vegvisirClientArguments.dict())
						
						client_cmd = ""
						client_proc = None
						if client.type == Endpoint.Type.DOCKER:
							with open("client.env", "w") as fp:
								Parameters.serialize_to_env_file(client_params, fp)
							
							# params += " ".join(client.additional_envs())
							client_cmd = (
								docker_compose_vars
								+ " docker compose up --abort-on-container-exit --timeout 1 "
								+ "client"
							)
							client_proc = self.spawn_parallel_subprocess(client_cmd, False, True)

						elif client.type == Endpoint.Type.HOST:
							for constructor in client.construct:
								constructor_command = constructor.serialize_command(client_params)
								logging.debug(f"Issuing client construct command [{constructor_command}]")
								_, out, err = self.spawn_blocking_subprocess(constructor_command, constructor.requires_root, True)
								if out is not None and len(out) > 0:
									logging.debug(f"Construct command STDOUT:\n{out}")
								if err is not None and len(err) > 0:
									logging.debug(f"Construct command STDERR:\n{err}")
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

						client_proc.terminate() # TODO redundant?
						if client.type == Endpoint.Type.HOST:
							# Doing this for docker will nullify the sensor system
							# Docker client logs are retrieved with "docker compose logs"
							out, err = client_proc.communicate()
							logging.debug(out.decode("utf-8"))
							logging.debug(err.decode("utf-8"))

						_, out, err = self.spawn_blocking_subprocess(docker_compose_vars + " docker compose logs --timestamps", False, True)
						logging.debug(out)
						logging.debug(err)

						_, out ,err = self.spawn_blocking_subprocess(docker_compose_vars + " docker compose down", False, True) # TODO TEMP
						logging.debug(out)

					# BREAKDOWN
					if client.type == Endpoint.Type.HOST:
						for destructor in client.destruct:
								destructor_command = destructor.serialize_command(client_params)
								logging.debug(f"Issuing client destruct command [{destructor_command}]")
								_, out, err = self.spawn_blocking_subprocess(destructor_command, destructor.requires_root, True)
								if out is not None and len(out) > 0:
									logging.debug(f"Destruct command STDOUT:\n{out}")
								if err is not None and len(err) > 0:
									logging.debug(f"Destruct command STDERR:\n{err}")

						_, out, err = self.spawn_blocking_subprocess("hostman remove --names=server4", True, False)
						logging.debug("Vegvisir: remove entry from hosts: %s", out.strip())
						if err is not None and len(err) > 0:
							logging.debug("Vegvisir: removing entry from hosts file resulted in error: %s", err)

					# Change ownership of docker output to running user
					try:
						real_username = getpass.getuser()
						real_primary_groupname = grp.getgrgid(os.getgid()).gr_name
						chown_to = f"{real_username}:{real_primary_groupname}"
						_, out, err = self.spawn_blocking_subprocess(f"chown -R {chown_to} {self._path_collection.log_path_permutation}", True, False)
						if len(err) > 0:
							raise VegvisirException(err)
						logging.debug(f"Changed ownership of output logs to {chown_to} | {self._path_collection.log_path_permutation}")
					except (KeyError, TypeError):
						logging.warning(f"Could not change log output ownership @ {self._path_collection.log_path_permutation}, groupname might not be found?")
					except VegvisirException as e:
						logging.warning(f"Could not change log output ownership [{e}] @ {self._path_collection.log_path_permutation}")

					self.hook_processor_queue.put((self.environment.post_run_hook, path_collection_copy))  # Queue is infinite, should not block

					experiment_permutation_counter += 1

					# TODO PLACE CORRECTLY
					logging.getLogger().removeHandler(log_handler)
					log_handler.close()  # TODO jherbots clean this and replace with nicer handler
		
		yield None, None, None, None, None

		# Halt the hook processors
		wait_for_hook_processors_counter = 0
		while True:
			if self.hook_processor_queue.qsize() == 0:
				self.hook_processor_request_stop = True
			states = [t.is_alive() for t in self.hook_processors]
			time.sleep(5)
			if not any(states):
				for t in self.hook_processors:
					t.join()
				break
			if wait_for_hook_processors_counter % 2 == 0:
				hooks_todo = self.hook_processor_queue.qsize()
				if hooks_todo > 0:
					print(f"Vegvisir is waiting for all hooks to process, approximately {self.hook_processor_queue.qsize()} request(s) still in queue.")
				else:
					print(f"Vegvisir is waiting for {sum(states)} hook processor(s) to stop. If this message persists, perform CTRL + C")
			wait_for_hook_processors_counter += 1


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