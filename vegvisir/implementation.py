from enum import Enum
from typing import List

class Role(Enum):
	CLIENT = 1
	SERVER = 2
	SHAPER = 3

class Type(Enum):
	DOCKER = "docker"
	APPLICATION = "application"

class Implementation:
	name: str = ""
	url: str = ""
	type: Type = ""

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

class Application(Implementation):
	command: str = ""

	def __init__(self, name: str, command: str, url: str):
		super().__init__(name, url)
		self.type = Type.APPLICATION
		self.command = command

class Shaper(Docker):
	scenarios: List[str] = []

	def __init__(self, name: str, image: str, url: str):
		super().__init__(name, image, url)
		self.scenarios = []