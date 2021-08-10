from enum import Enum
from typing import List

class Role(Enum):
	CLIENT = 1
	SERVER = 2
	SHAPER = 3

class Implementation:
	name: str = ""
	image: str = ""
	url: str = ""
	role: List[Role] = []

	def __init__(
		self,
		name: str,
		image: str,
		url: str,
		roles: List[Role]
	):
		self.name = name
		self.image = image
		self.url = url
		self.role = roles

class Shaper(Implementation):
	scenarios: List[str] = []

	def __init__(self, name: str, image: str, url: str, roles: List[Role]):
		super().__init__(name, image, url, roles)
		self.scenarios = []