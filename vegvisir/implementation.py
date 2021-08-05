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
	roles: List[Role] = []

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
		self.roles = roles