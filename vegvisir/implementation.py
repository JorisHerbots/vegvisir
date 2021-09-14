from enum import Enum
from typing import List

class Role(Enum):
	CLIENT = 1
	SERVER = 2
	SHAPER = 3

class Type(Enum):
	DOCKER = "docker"
	APPLICATION = "application"

class RunStatus(Enum):
	WAITING = "waiting"
	RUNNING = "running"
	DONE = "done"

class Implementation:
	name: str = ""
	url: str = ""
	type: Type = ""
	active: bool = False
	status: RunStatus = RunStatus.WAITING
	env_vars: List[str]
	env: List[str]

	def __init__(
		self,
		name: str,
		url: str,
	):
		self.name = name
		self.url = url

	def additional_envs(self) -> List[str]:
		return self.env

class Image():
	url: str = ""
	active: bool = False
	repo: str = ""
	name: str = ""
	tag: str = ""

	def __init__(self, url: str):
		self.url = url
		self.repo = get_repo_from_image(url)
		self.name = get_name_from_image(url)
		self.tag = get_tag_from_image(url)

class Docker(Implementation):
	images: List[Image] = []
	original_image: str = ""
	image_name: str = ""
	
	curr_image: Image = None

	def __init__(self, name: str, image: str, url: str):
		super().__init__(name, url)
		self.type = Type.DOCKER
		self.original_image = image
		self.images = [Image(image)]

		self.image_name = get_name_from_image(image)

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

class Command():
	sudo: bool = False
	replace_tilde: bool = True
	command: str = ""

class Application(Implementation):
	command: str = ""
	setup: List[Command] = []

	def __init__(self, name: str, command: str, url: str):
		super().__init__(name, url)
		self.type = Type.APPLICATION
		self.command = command

class Scenario():
	name: str = ""
	arguments: str = ""
	active: bool = False
	status: RunStatus = RunStatus.WAITING

	def __init__(self, name: str, arguments: str):
		self.name = name
		self.arguments = arguments

class Shaper(Docker):
	scenarios: List[Scenario] = []

	def __init__(self, name: str, image: str, url: str):
		super().__init__(name, image, url)
		self.scenarios = []