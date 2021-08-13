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

	def __init__(
		self,
		name: str,
		url: str,
	):
		self.name = name
		self.url = url

class Docker(Implementation):
	image: str = ""

	def __init__(self, name: str, image: str, url: str):
		super().__init__(name, url)
		self.type = Type.DOCKER
		self.image = image

class Command():
	sudo: bool = False
	replace_tilda: bool = True
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