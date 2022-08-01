from enum import Enum
from typing import List
from datetime import datetime
import logging
import os
import pathlib
import sys
import subprocess
from time import time, sleep
from typing import List
import json
import tempfile
import re
import shutil
from pathlib import Path

# TODO: also start join(testcase.additional_containers())
# When server and shaper start

from .testcases import Perspective, ServeTest, StaticDirectory, Status, TESTCASES, TestCase, TestEndTimeout, TestEndUntilDownload, TestResult

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


# Wrapper for a terminal command
# Command can be executed in a new process by running execute
# Variables
#	sudo			: if the command should be run as sudo or not 
#	replace_tilde	: if ~ should be replaced by Path.home() or not
#	command 		: command in string format, 
class Command:
	sudo: bool = False
	replace_tilde: bool = True
	command: str = ""

	def __init__(self, command):
		self.command = command 

	# Formats the command (self.command) by filling in log dir locations if present
	# and (if enabled by self.replace_tilde) replacing ~ with home path 
	# Variables
	#   client_log_dir : client log dir location of client
	#	server_log_dir : server log dir location of client
	#	shaper_log_dir : shaper log dir location of client
	# Returns 
	#	string containing formatted command
	def _format(self, client_log_dir_local : str, server_log_dir_local : str, shaper_log_dir_local) -> str:
		formatted_command = self.command.format(client_log_dir=client_log_dir_local, server_log_dir=server_log_dir_local, shaper_log_dir=shaper_log_dir_local)
		
		if self.replace_tilde:
			self.command_formatted = formatted_command.replace("~", str(Path.home()))

		logging.debug("Vegvisir: formatted command: %s", formatted_command)
		return formatted_command

	# Execute the command 
	# Parameters
	#   client_log_dir : client log dir location of client
	#	server_log_dir : server log dir location of client
	#	shaper_log_dir : shaper log dir location of client
	def execute(self, client_log_dir_local : str, server_log_dir_local : str, shaper_log_dir_local : str, sudo_password: str):
		out = ""

		formatted_command = self._format(client_log_dir_local, server_log_dir_local, shaper_log_dir_local)

		if self.sudo:
			net_proc = subprocess.Popen(
			["sudo", "-S"] + formatted_command.split(" "),
			shell=False,
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT
		)
			o, e = net_proc.communicate(sudo_password.encode())
			out += str(o) + "\n" + str(e)
		else:
			proc = subprocess.run(
				formatted_command,
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
			out += proc.stdout.decode("utf-8")
		
		logging.debug("Vegvisir: command executed: %s\n%s", formatted_command, out) 




# Implementation base class 
# Contains information about avaiable client/shaper/server implementation
class Implementation:
	name: str = ""
	url: str = ""
	role: Role
	configurable_environment_variables: List[str]

	def __init__(self, name: str, url: str):
		self.name = name 

		self.url = url 

	def get_configureable_environment_variables(self):
		
		temp_list = []

		for item in self.configurable_environment_variables:
			try:	
				if isinstance(item, str):
					temp_list.append(item)
				logging.debug("item:")
				logging.debug(item)
			except:
				pass
		
		return temp_list


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


# Parent class of Implementation specifically for implementations that use Docker
# Variables 
#	image 	: 
class DockerImplementation(Implementation):
	image : str = ""
	repo: str = ""
	tag: str = ""


	def __init__(self, name, image, url):
		super().__init__(name, url)
		self.type = Type.DOCKER
		self.image = image
		
		self.repo = get_repo_from_image(url)
		#self.name = get_name_from_image(url)
		self.tag = get_tag_from_image(url)

	


# Parent class of Implementation specifically for native implementations (executables) that do not use Docker
class NativeImplementation(Implementation):
	setup : List[Command] = []


	def __init__(self, name, command, url):
		super().__init__(name, url)
		self.type = Type.APPLICATION

		# TODO: make command of Command class
		self.command = command


# Specific scenario (of configuration parameters) for a client/server/shaper implementation
# Variables
# 	name 							 : name of the scenario, for example "Chrome with settings x, y and z"
#   arguments 						 : to be used with shaper, for example: "\"simple 15 10\""
#   configured_environment_variables : environment variables to be used with client/server, list is in the same order as 
# 									   configurable_environment_variables in implementation
#	implementation 					 : implementation this scenario belongs to (multiple scenarios can have 
# 									   the same implementation) 
class Scenario: 
	name: str = ""
	arguments: str = ""
	configured_environment_variables: List[str] = []
	implementation: Implementation

	def __init__(self, name : str,  implementation : Implementation, arguments = "", configurable_environment_variables = []):
		self.name = name
		self.implementation = implementation	
		self.arguments = arguments 
		self.configured_environment_variables = configurable_environment_variables	

# TODO: documentation
class LogFileFormatter(logging.Formatter):
	def format(self, record):
		msg = super(LogFileFormatter, self).format(record)
		# remove color control characters
		return re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]").sub("", msg)






