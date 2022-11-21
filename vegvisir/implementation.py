from enum import Enum
import re
import sys
from typing import Dict, List, TextIO, Tuple
# class Role(Enum):
# 	CLIENT = 1
# 	SERVER = 2
# 	SHAPER = 3

# class Type(Enum):
# 	DOCKER = "docker"
# 	APPLICATION = "application"

# class RunStatus(Enum):
# 	WAITING = "waiting"
# 	RUNNING = "running"
# 	DONE = "done"

# class Implementation:
# 	name: str = ""
# 	url: str = ""
# 	type: Type = ""
# 	role: Role = None
# 	active: bool = False
# 	status: RunStatus = RunStatus.WAITING
# 	env_vars: List[str]
# 	env: List[str]
# 	arguments: Dict[str, bool] = {}
# 	_required_arguments: List[str] = []

# 	def __init__(self, name: str, url: str):
# 		self.name = name
# 		self.url = url  # TODO jherbots REMOVE

# 	def __repr__(self) -> str:
# 		return f"Implementation{{ name: {self.name}, type: {self.type}, role {self.role} }}"

# 	def __str__(self) -> str:
# 		return f"Implementation [{self.name}] type [{self.type}] role [{self.role}]"

# 	def add_argument(self, arg: str, required: bool = False):
# 		self.arguments[arg] = required
# 		if required:
# 			self._required_arguments.append(arg)

# class Image():
# 	url: str = ""
# 	active: bool = False
# 	repo: str = ""
# 	name: str = ""
# 	tag: str = ""

# 	def __init__(self, url: str):
# 		self.url = url
# 		self.repo = get_repo_from_image(url)
# 		self.name = get_name_from_image(url)
# 		self.tag = get_tag_from_image(url)

# class Docker(Implementation):
# 	images: List[Image] = []
# 	original_image: str = ""
# 	image_name: str = ""
	
# 	curr_image: Image = None

# 	# TODO JHERBOTS Remove URL
# 	def __init__(self, name: str, image: str, url: str = ""):
# 		super().__init__(name, url)
# 		self.type = Type.DOCKER
# 		self.original_image = image
# 		self.images = [Image(image)]

# 		self.image_name = get_name_from_image(image)

	
# 	def urlnal_envs(self) -> List[str]:
# 		env_file_path = ''
# 		if self.role == Role.CLIENT:
# 			env_file_path = 'client'
# 		elif self.role == Role.SERVER:
# 			env_file_path = 'server'
# 		elif self.role == Role.SHAPER:
# 			env_file_path = 'shaper'
# 		env_file_path += '.env'

# 		with open(env_file_path, 'w') as env_file:
# 			for e in self.env:
# 				env_file.write(e+'\n')

# 		return self.env

# def get_name_from_image(image):
# 	return image.split('/')[-1].split(':')[0]

# def get_repo_from_image(image):
# 	repo = None
# 	try:
# 		repo = image.split('/')[-2]
# 	except:
# 		repo = None
# 	return repo

# def get_tag_from_image(image):
# 	split = image.split(':')
# 	if len(split) == 1:
# 		return ""
# 	return split[-1]

# class Command():
# 	sudo: bool = False
# 	replace_tilde: bool = True # TODO Jherbots remove
# 	command: str = ""

# 	def __init__(self, command: str, sudo: bool) -> None:
# 		self.command = command
# 		self.sudo = sudo

# 	def get_command(arguments: list[str]):
# 		pass

# class Application(Implementation):
# 	command: str = ""
# 	setup: List[Command] = []

# 	def __init__(self, name: str, command: str, url: str = ""): # TODO jherbots remove url
# 		super().__init__(name, url)
# 		self.type = Type.APPLICATION
# 		self.command = command

# class Scenario():
# 	name: str = ""
# 	arguments: str = ""
# 	active: bool = False
# 	status: RunStatus = RunStatus.WAITING

# 	def __init__(self, name: str, arguments: str = ""):  # TODO jherbots remove url
# 		self.name = name
# 		self.arguments = arguments

# 	def __repr__(self) -> str:
# 		return f"Scenario{{ {self.arguments} active [{self.active}]}}"  # TODO jherbots clean

# class Shaper(Docker):
# 	scenarios: List[Scenario] = []

# 	def __init__(self, name: str, image: str, url: str = "" ):  # TODO jherbots remove url
# 		super().__init__(name, image, url)
# 		self.scenarios = []


################## NEW #################

class VegvisirParameterException(Exception):
	pass

class VegvisirArgumentException(Exception):
	pass

class VegvisirCommandException(Exception):
	pass


class HostCommand:
	def __init__(self, command: str, root_required: bool = False) -> None:
		self.command = command
		self.requires_root = root_required

	def serialize_command(self, hydrated_parameters: Dict[str, str]):  # TODO reevaluate
		# try:
		# 	return self.command.format(**hydrated_parameters)  # TODO catch key errors
		# except KeyError as e:
		# 	raise VegvisirCommandException(f"Command [{self.command}] contains an unknown parameter [{e.args[0]}]")
		# except TypeError:
		# 	raise VegvisirCommandException(f"Command [{self.command}] serialized with non-dict type input.")
		return ArgumentTemplate.substitute(self.command, hydrated_parameters)

class ArgumentTemplate:
	# pattern = re.compile(r"\$(?:(?:{(?P<parameter>(?:[A-Z]+[A-Z0-9]*))})|(?P<escaped>\${(?:[A-Z]+[A-Z0-9]*)}))")
	pattern = re.compile(r"\$(?:(?:\{(?P<parameter>(?:[A-Z0-9_-]+))\})|(?P<escaped>\$)|(?:(?P<invalid>)))")

	def _sub(template: str, hydrated_parameters: Dict[str, str], visited_nodes=[]):
		def sub_rule(match_object: re.Match):
			nonlocal visited_nodes
			if match_object.group("escaped") is not None:
				return match_object.group("escaped")
			if match_object.group("parameter") is not None:
				param = match_object.group("parameter")
				if param not in hydrated_parameters:
					raise VegvisirArgumentException(f"Argument [{template}] references unknown parameter [{param}].")
				if param in visited_nodes:
					raise VegvisirArgumentException(f"Cycle detected [{'->'.join([f'${{{node}}}' for node in visited_nodes])}->${{{param}}}]")
				current_cycle_visited_nodes = list(visited_nodes)  # Each branch requires a copy of the list
				current_cycle_visited_nodes.append(param)
				collapsed_arg = ArgumentTemplate._sub(hydrated_parameters[param], hydrated_parameters, current_cycle_visited_nodes)
				hydrated_parameters[param] = collapsed_arg  # Some memoization can't hurt
				return collapsed_arg
			if match_object.group("invalid") is not None:
				debug_template = template
				if len(template) > 60:
					debug_template = template[match_object.start()-30:match_object.start()+30]  # Python does not care about slicing out of bounds
				error = "Invalid parameter syntax:\n"
				debug_template = debug_template.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
				error += f"\t\"{debug_template}\"\n"
				replace_offset = debug_template.count("\\n", 0, match_object.start()) + debug_template.count("\\t", 0, match_object.start()) + debug_template.count("\\r", 0, match_object.start())
				error += "\t" + (" " * (match_object.start() + 1 + replace_offset)) + f"^ Starting point of invalid syntax"
				raise VegvisirArgumentException(error)
		return ArgumentTemplate.pattern.sub(sub_rule, template)

	def substitute(template: str, hydrated_parameters: Dict[str, str], override_provided_parameters=False):
		"""
		Substitute arguments matched by the pattern regex with their respective contents from the uncollapsed hydrated_parameters
		hydrated_parameters can contain values which themselve reference arguments, postulating the need for recursive substitution and cycle checking
		This method will collapse and cycle check the provided hydrated_parameters such that the initial provided template can correctly be substituted 
		"""
		try:
			return ArgumentTemplate._sub(template, hydrated_parameters if override_provided_parameters else dict(hydrated_parameters), [])
		except RecursionError:
			raise VegvisirArgumentException(f"Argument [{template}] too deeply nested. Max recursion depth of {sys.getrecursionlimit()} has been reached.")


class Parameters:
	_vegvisir_provided_params: List[str] = ["ORIGIN", "CLIENT_LOG_DIR", "CERT_FINGERPRINT", "WAITFORSERVER", "SCENARIO", "ROLE", "TESTCASE", "QLOGDIR", "SSLKEYLOGFILE"]

	def __init__(self, parameters: Dict[str, bool] | None = None) -> None:
		self.params: List[str] = []
		self._required_params: List[str] = []

		if not parameters:
			return  # TODO catch silent fail?
		
		if type(parameters) == dict:
			for key, required in parameters.items():
				self.params.append(key)
				if required:
					self._required_params.append(key)
		elif type(parameters) == list:
			for key in parameters:
				self.params.append(key)
				self._required_params.append(key)

		forbidden_params = set(self.params) & set(Parameters._vegvisir_provided_params)
		if len(forbidden_params) > 0:
			raise VegvisirParameterException(f"Parameter list contains system parameters, the following parameters {list(forbidden_params)} are not allowed to be user defined.")

	def hydrate_with_arguments(self, user_params: Dict[str, str], vegvisir_params: Dict[str, str] = {}) -> Dict[str, str]:  # TODO jherbots filter out vegvisir args
		hydrated_params: Dict[str, str] = {}
		if user_params is None or not type(user_params) is dict:
			return  {} # TODO potential silent failure?

		# User provided arguments
		filtered_args = user_params.keys() & self.params
		if not all(req in filtered_args for req in self._required_params) or len(filtered_args) < len(self._required_params):
			raise VegvisirArgumentException("Not all required parameters are provided.")
		
		for arg in filtered_args:
			hydrated_params[arg] = user_params[arg]

		# System provided arguments
		filtered_args = vegvisir_params.keys() & Parameters._vegvisir_provided_params
		for arg in filtered_args:
			hydrated_params[arg] = vegvisir_params[arg]

		# Collapse params to one level
		for (param, arg) in hydrated_params.items():
			hydrated_params[param] = ArgumentTemplate.substitute(hydrated_params[param], hydrated_params, True)

		return hydrated_params

	def hydrate_with_empty_arguments(self) -> Dict[str, str]:
		empty_user_args: Dict[str, str] = {arg:"" for arg in self.params}
		empty_system_args: Dict[str, str] = {arg:"" for arg in Parameters._vegvisir_provided_params}
		return self.hydrate_with_arguments(empty_user_args, empty_system_args)

	def can_input_fit_arguments(self, input_args: List[str]) -> Tuple[bool, List[str], List[str]]:  # TODO jherbots filter out vegvisir args
		"""
		Casting to set is safe as we assume only 1 entry per argument
		"""
		input_args = set(input_args if input_args else [])
		expected_args = set(self.params)
		expected_required_args = set(self._required_params)

		invalid_args = input_args - expected_args
		valid_args = expected_args & input_args
		missing_req_args = expected_required_args - valid_args # TODO add vegvisir params check!
		return len(missing_req_args) == 0, list(missing_req_args), list(invalid_args)  # TODO jherbots sanity check this

	def serialize_to_env_inline(self, hydrated_params: Dict[str, str]):
		inline_env = ""
		for (param, arg) in hydrated_params.values():
			inline_env += f"{param}={arg} "
		return inline_env

	def serialize_to_env_file(hydrated_params: Dict[str, str], file: TextIO):
		for (key, value) in hydrated_params.items():
			file.write(f"{key}={value}\n")

	def __repr__(self) -> str:
		return f"Parameters<params: {self.params}, required_params: {self._required_params}>"


class Scenario:
	def __init__(self, command: str, parameters: Parameters) -> None:
		self.command: str = command
		self.parameters: Parameters = parameters

	def __repr__(self) -> str:
		return f"Scenario<command: '{self.command}', parameters: {self.parameters}>"

class DockerImage:
	def __init__(self, image: str) -> None:
		self._image = image

	@property
	def full(self):
		return self._image

	@property
	def name(self):
		return get_name_from_image(self._image)

	@property
	def repo(self):
		return get_repo_from_image(self._image)

	@property
	def tag(self):
		return get_tag_from_image(self._image)

class Endpoint:
	"""
	Client and server representation
	Servers can only assume the docker type
	"""
	class Type(Enum):
		DOCKER = "docker"
		HOST = "host"
	
	def __init__(self, name: str, pretty_name: str, program_type: Type, program: DockerImage | HostCommand, params: Parameters) -> None:
		self.name: str = name
		self.pretty_name = pretty_name
		self.type: Endpoint.Type = program_type
		self.image = program if type(program) is DockerImage else None
		self.command = program if type(program) is HostCommand else None
		self.parameters: Parameters = params
		self.setup: List[HostCommand] = []
		
	def __repr__(self) -> str:
		return f"Endpoint<{self.name}, {self.type.name}, {self.image if self.image is not None else self.command}>"


class Shaper:
	def __init__(self, name: str, pretty_name: str, image: DockerImage) -> None:
		self.name: str = name
		self.image = image
		self.pretty_name = pretty_name
		self.scenarios: Dict[str, Scenario] = {}

	def __repr__(self) -> str:
		return f"Shaper<{self.name}, scenarios {self.scenarios}>"


# Utils
def get_name_from_image(image):
	return image.split('/')[-1].split(':')[0]

def get_repo_from_image(image):
	repo = None
	try:
		repo = image.split('/')[-2]
	except:
		repo = None
	return repo

def get_tag_from_image(image):
	split = image.split(':')
	if len(split) == 1:
		return ""
	return split[-1]