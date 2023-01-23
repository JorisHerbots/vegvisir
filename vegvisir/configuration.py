import json
import logging
import os
from typing import Dict, List, Set
from vegvisir import environments
from vegvisir.data import ExperimentPaths, VegvisirArguments
from vegvisir.environments.base_environment import BaseEnvironment
from vegvisir.exceptions import VegvisirException, VegvisirArgumentException, VegvisirCommandException, VegvisirInvalidExperimentConfigurationException, VegvisirInvalidImplementationConfigurationException, VegvisirConfigurationException
from vegvisir.implementation import DockerImage, Endpoint, HostCommand, Parameters, Scenario, Shaper


class Configuration:
	def __init__(self, implementations_path: str | None = None, experiment_path: str | None = None) -> None:
		
		self._implementations_configuration_loaded = False
		self._experiment_configuration_loaded = False

		self._path_collection = ExperimentPaths()
			
		self._client_endpoints: Dict[str, Endpoint] = {}
		self._server_endpoints: Dict[str, Endpoint] = {}
		self._shapers: Dict[str, Shaper] = {}

		self._client_configurations: List[Dict] = []
		self._server_configurations: List[Dict] = []
		self._shaper_configurations: List[Dict] = []

		self._www_path = None

		self._iterations = 1

		self._environment: BaseEnvironment = None

		# Provide developer with the freedom of already loading the provided configuration paths
		if implementations_path is not None:
			self.load_implementations_from_file(implementations_path)
		if experiment_path is not None:
			self.load_experiment_from_file(experiment_path)

	@property
	def client_endpoints(self):
		self._validate_and_raise_load(self._implementations_configuration_loaded, "client_endpoints", "implementations")
		return self._client_endpoints

	@property
	def server_endpoints(self):
		self._validate_and_raise_load(self._implementations_configuration_loaded, "server_endpoints", "implementations")
		return self._server_endpoints

	@property
	def shapers(self):
		self._validate_and_raise_load(self._implementations_configuration_loaded, "shapers", "implementations")
		return self._shapers

	@property
	def client_configurations(self):
		self._validate_and_raise_load(self._experiment_configuration_loaded, "client_configurations", "experiment")
		return self._client_configurations

	@property
	def server_configurations(self):
		self._validate_and_raise_load(self._experiment_configuration_loaded, "server_configurations", "experiment")
		return self._server_configurations

	@property
	def shaper_configurations(self):
		self._validate_and_raise_load(self._experiment_configuration_loaded, "shaper_configurations", "experiment")
		return self._shaper_configurations

	@property
	def www_path(self):
		self._validate_and_raise_load(self._experiment_configuration_loaded, "www_path", "experiment")
		return self._www_path

	@property
	def iterations(self):
		self._validate_and_raise_load(self._experiment_configuration_loaded, "iterations", "experiment")
		return self._iterations

	@property
	def environment(self):
		self._validate_and_raise_load(self._experiment_configuration_loaded, "environment", "experiment")
		return self._environment

	@property
	def path_collection(self):
		# Patch collection requires self-checks on values
		return self._path_collection

	@property
	def docker_images(self):
		self._validate_and_raise_load(self._implementations_configuration_loaded, "docker_images", "implementations")
		images = []
		for endpoint in list(self._client_endpoints.values()) + list(self._server_endpoints.values()):
			if endpoint.type == Endpoint.Type.DOCKER:
				images.append(endpoint.image.full)
		for shaper in self._shapers.values():
			images.append(shaper.image.full)
		return images

	def _validate_and_raise_load(self, config_bool: bool, getter: str, required_config_name: str):
		if not config_bool:
			raise VegvisirConfigurationException(f"Access to [{getter}] property of the Configuration is only possible after loading the {required_config_name} configuration.")

	def load_configurations_from_json_file(self, implementations_path: str, experiment_path: str) -> None:
		self.load_implementations_from_file(implementations_path)
		self.load_experiment_from_file(experiment_path)

	def load_implementations_from_file(self, implementations_path: str) -> None:
		"""
		Load client, shaper and server implementations from JSON configuration file
		Warning: Calling this function will overwrite current list of implementations!
		"""
		self._client_endpoints = {}
		self._server_endpoints = {}
		self._shapers = {}

		try:
			with open(implementations_path) as f:
				implementations = json.load(f)
			self._load_implementations_from_dict(implementations)
			self._path_collection.implementations_configuration_file_path = implementations_path
		except FileNotFoundError as e:
			raise VegvisirConfigurationException(f"Implementations file [{implementations_path}] not found | {e}")
		except json.JSONDecodeError as e:
			raise VegvisirInvalidImplementationConfigurationException(f"Failed to decode provided implementations JSON [{implementations_path}] | {e}")

	def _load_implementations_from_dict(self, implementations: Dict) -> None:
		"""
		Load implementation from a JSON file
		If truly loaded via json.load, duplicates will be automatically be eliminated
		"""
		if self._implementations_configuration_loaded:
			raise VegvisirConfigurationException("Configuration objects can not reload configurations. Create a new configuration object for multiple configurations.")
		self._implementations_configuration_loaded = True

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

	def load_experiment_from_file(self, experiment_path: str) -> None:
		try:
			with open(experiment_path) as f:
				configuration = json.load(f)
			self._load_and_validate_experiment_from_dict(configuration)
			self._path_collection.experiment_configuration_file_path = experiment_path
		except FileNotFoundError as e:
			raise VegvisirConfigurationException(f"Implementations file [{experiment_path}] not found | {e}")
		except json.JSONDecodeError as e:
			raise VegvisirInvalidExperimentConfigurationException(f"Failed to decode experiment configuration JSON [{experiment_path}] | {e}")

	def _load_and_validate_experiment_from_dict(self, configuration: Dict) -> None:
		"""
		Load and validate is a bad smell, but then again why bother :)
		"""
		if not self._implementations_configuration_loaded:
			raise VegvisirConfigurationException("Configuration objects can not load experiment configurations without implementations being loaded first.")
		if self._experiment_configuration_loaded:
			raise VegvisirConfigurationException("Configuration objects can not reload configurations. Create a new configuration object for multiple configurations.")
		self._experiment_configuration_loaded = True

		CLIENTS_KEY = "clients"
		SERVERS_KEY = "servers"
		SHAPERS_KEY = "shapers"

		if not type(configuration) is dict:
			raise VegvisirInvalidExperimentConfigurationException("Configuration is not a dictionary.")

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
			self._www_path = os.path.abspath(settings["www_dir"])
		else:
			self._www_path = os.path.join(os.getcwd(), "www")
		if not os.path.exists(self._www_path):
			raise VegvisirInvalidExperimentConfigurationException(f"WWW path does not exist [{self._www_path}]")

		iterations = settings.get("iterations", 1)
		if type(iterations) is str and not iterations.isdigit():
			raise VegvisirInvalidExperimentConfigurationException("Setting 'iterations' must be > 0.")
		try:
			self._iterations = int(iterations)
		except ValueError:
			raise VegvisirInvalidExperimentConfigurationException("Setting 'iterations' must be > 0.")
		if self._iterations <= 0:
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
		self._environment = environments.available_environments[environment_name]()
				
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
				self._environment.add_sensor(environments.available_sensors[sensor["name"]](**sensor_arguments))
			except TypeError as e:
				raise VegvisirInvalidImplementationConfigurationException(f"Sensor [{sensor['name']}] can not be initialized with the provided arguments. Make sure all required initialization parameters are provided [f{e}]")