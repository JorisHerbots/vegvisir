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
import copy


from .runner import Runner
from .implementation import Implementation, Role, Type, RunStatus, Command, DockerImplementation, NativeImplementation, Scenario, LogFileFormatter
from .testcases import *

# Class that manages all implementations and scenarios and starts testruns
#  
class Manager:	

	_possible_client_implementations = []
	_possible_shaper_implementations = []
	_possible_server_implementations = []
	_possible_testcases = []

	_active_clients : List[Scenario] = []
	_active_shapers : List[Scenario] = []
	_active_servers : List[Scenario] = []
	_active_testcases : List[TestCase] = []

	sudo_password = ""

	def __init__(self, sudo_password):
		logging.basicConfig(level=logging.INFO)
		self.sudo_password = sudo_password
		self._read_implementations_file("implementations.json")

		for t in TESTCASES:
			self._possible_testcases.append(t())

		#self._active_testcases.append(self._possible_testcases[0])
		



	# params
	# 	file: path of implementations file to be read
	# pre 
	#	file has to be valid, no type of checking is done
	# post 
	# 	_clients, _shapers, _servers are filled
	def _read_implementations_file(self, file: str):
		self._clients = []
		self._servers = []
		self._shapers = []

		with open(file) as f:
			implementations = json.load(f)

		self.set_implementations(implementations)

	# params
	# 	implementations
	# post 
	# 	_clients, _shapers, _servers are filled
	def set_implementations(self, implementations):
		logging.debug("Vegvisir: Loading implementations:")
		
		for name in implementations:
			attrs = implementations[name]

			active = False
			if "active" in attrs:
				active = attrs["active"]

			env = []
			if "env" in attrs:
				env = attrs["env"]

			roles = []
			for role in attrs["role"]:
				if role == "client":
					roles.append(Role.CLIENT)
					client_settings = attrs["client"]
					impl = None
					if client_settings["type"] == Type.DOCKER.value:
						impl = DockerImplementation(name, attrs["image"], attrs["url"])
					elif client_settings["type"] == Type.APPLICATION.value:
						impl = NativeImplementation(name, client_settings["command"], attrs["url"])
						if "setup" in client_settings:
							for cmd in client_settings["setup"]:
								scmd = Command(cmd["command"])
								scmd.sudo = cmd["sudo"]
								scmd.replace_tilde = cmd["replace_tilde"]
								impl.setup.append(scmd)
					impl.configurable_environment_variables = env
					impl.role = Role.CLIENT
					self._possible_client_implementations.append(impl)
                
                    
					# if client_settings["type"] == Type.APPLICATION.value:
					# 	self._active_clients.append(Scenario("noname", impl))

				elif role == "server":
					roles.append(Role.SERVER)
					impl = DockerImplementation(name, attrs["image"], attrs["url"])
					impl.configurable_environment_variables = env
					impl.role = Role.SERVER
					self._possible_server_implementations.append(impl)
					#self._active_servers.append(Scenario("noname", impl))

				elif role == "shaper":
					roles.append(Role.SHAPER)
					impl = DockerImplementation(name, attrs["image"], attrs["url"])
					impl.configurable_environment_variables = env
					impl.role = Role.SHAPER

					# TODO: currently sets all shaper scenarios active
					if "scenarios" in attrs:
						for scenario in  attrs["scenarios"]:
							scen_attrs = attrs["scenarios"][scenario]
							scen = Scenario(scenario, implementation=impl, arguments= scen_attrs["arguments"])
							#self._active_shapers.append(scen)
        
					self._possible_shaper_implementations.append(impl)
            

			logging.debug("Vegvisir: \tloaded %s as %s", name, attrs["role"])
		
		
		# TODO: add scan image repos again
		#self._scan_image_repos()



	def add_active_implementation(self, implementation): 
		lookup_list = None 
		insert_list = None

		if implementation["role"][0] == "client":
			lookup_list = self._possible_client_implementations
			insert_list = self._active_clients
		elif implementation["role"][0] == "shaper":
			lookup_list = self._possible_shaper_implementations
			insert_list = self._active_shapers
		elif implementation["role"][0] == "server":
			lookup_list = self._possible_server_implementations
			insert_list = self._active_servers
		
		python_implementation = None

		for item in lookup_list:
			print(item.name)
			if item.name == implementation["id"]:
				python_implementation = item 
				print(item.name)
				break 

		environment_variables = []
		argument = ""

		if "env" in implementation:
			for variable in implementation["env"]:
				logging.debug("variable")
				logging.debug(variable)
				if variable["name"] == "argument":
					logging.debug("adding as argumnet")
					argument = variable["value"]
				else:
					logging.debug("adding as env")
					environment_variables.append(variable["value"])

		scen = Scenario(implementation["active_id"], python_implementation, argument, environment_variables)

		insert_list.append(scen)

	def add_active_testcase(self, testcase):

		python_testcase = ""

		for item in self._possible_testcases:
			logging.debug(testcase)
			if item.id == testcase["id"]:
				python_testcase = copy.deepcopy(item)
				break 

		if "parameters" in testcase:

			parameters_dict = {}
			
			for parameter in testcase["parameters"]:
				parameters_dict[parameter["name"]] = parameter["value"]

			python_testcase.set_parameters(parameters_dict)

		self._active_testcases.append(python_testcase)


	# Runs all tests for all active clients, shapers, servers and test case permutations
	def run_tests(self):
		for server in self._active_servers:
			for shaper in self._active_shapers:
				for client in self._active_clients:
					for test_case in self._active_testcases:
						runner = Runner(self.sudo_password)
						runner.run_test(client, shaper, server, test_case)
						

