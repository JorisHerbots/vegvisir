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

from .run_logger import RunLogger
from .implementation import Implementation, Role, Type, RunStatus, Command, DockerImplementation, NativeImplementation, Scenario, LogFileFormatter
from .testcases import *

class Runner:
	sudo_password : str = ""

	def __init__(self, sudo_password):
		self.sudo_password = sudo_password

	# Setups network when using NativeImplementation client
	# TODO: better documentation
	def _setup_network_for_test_application(self):
		net_proc = subprocess.Popen(
					["sudo", "-S", "ip", "route", "del", "193.167.100.0/24"],
					shell=False,
					stdin=subprocess.PIPE,
					stdout=subprocess.PIPE,
					stderr=subprocess.STDOUT
				)
		out, err = net_proc.communicate(self.sudo_password.encode())
		logging.debug("Vegvisir: network setup: %s", out.decode("utf-8"))
		if not err is None:
			logging.debug("Vegvisir: network error: %s", err.decode("utf-8"))
		net_proc = subprocess.Popen(
			["sudo", "-S", "ip", "route", "add", "193.167.100.0/24", "via", "193.167.0.2"],
			shell=False,
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT
		)
		out, err = net_proc.communicate(self.sudo_password.encode())
		logging.debug("Vegvisir: network setup: %s", out.decode("utf-8"))
		if not err is None:
			logging.debug("Vegvisir: network error: %s", err.decode("utf-8"))
		net_proc = subprocess.Popen(
			["sudo", "-S", "./veth-checksum.sh"],
			shell=False,
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT
		)
		out, err = net_proc.communicate(self.sudo_password.encode())
		logging.debug("Vegvisir: network setup: %s", out.decode("utf-8"))
		if not err is None:
			logging.debug("Vegvisir: network error: %s", err.decode("utf-8"))


	# Runs client setup by executing the commands in the setup list
	# Pre
	# 	implementation is of subclass NativeImplementation
	#	implementation has role = CLIENT 
	# Post
	# 	client is setup and ready for (use for) testing
	def _run_client_setup(self, implementation: Implementation, run_logger):		
		for command in implementation.setup:
			command.execute(run_logger.client_log_dir_local, run_logger.server_log_dir_local, run_logger.shaper_log_dir_local, self.sudo_password)
		
	# Get parameters for run
	# TODO: better documentation
	def _get_run_parameters(self, testcase, server: Implementation, shaper : Scenario, client : Implementation) -> str:
		
		client_image = "none"
		if isinstance(client, DockerImplementation):
			client_image = client.image

		params = (
			"WAITFORSERVER=server:443 "

			"TESTCASE_CLIENT=" + testcase.testname(Perspective.CLIENT) + " "
			"REQUESTS=\"" + testcase.request_urls + "\"" + " "

			"DOWNLOADS=" + testcase.download_dir() + " "
			"SERVER=" + server.image + " "
			"TESTCASE_SERVER=" + testcase.testname(Perspective.SERVER) + " "
			"WWW=" + testcase.www_dir() + " "
			"CERTS=" + testcase.certs_dir() + " "

			"SHAPER=" + shaper.implementation.image + " "
			
			# TODO: test if this works
			"SHAPERSCENARIO=" + shaper.arguments + " "

			"SERVER_LOGS=" + "/logs" + " "
			"CLIENT_LOGS=" + "/logs" + " "

			"CLIENT=" + client_image + " "	# required for compose v2
		)

		params += " ".join(testcase.additional_envs())
		logging.debug(shaper.implementation.get_configureable_environment_variables())
		params += " ".join(shaper.implementation.get_configureable_environment_variables())
		params += " ".join(server.get_configureable_environment_variables())

	
		if client.type == Type.DOCKER:
			params += " ".join(client.get_configureable_environment_variables())

		logging.info("Parameters: " + params)
		return params

	# shuts down all running docker containers
	# TODO: better documentation
	def _shut_down_docker_containers(self, params):
		try:
			logging.debug("Vegvisir: shutting down containers")
			proc = subprocess.run(
				params + " docker-compose down",
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
			logging.debug("Vegvisir: shut down successful: %s", proc.stdout.decode("utf-8"))
		except Exception as e:
			logging.debug("Vegvisir: subprocess error while shutting down: %s", str(e))		

	# Runs (tests) client
	# Pre
	# 	scenario.implementation is of subclass NativeImplementation or DockerImplementation
	#	scenario.implementation has role = CLIENT
	# 	shaper and server are running
	# Post
	# 	client is running / ran
	# Returns
	#	process running client
	def run_client(self, scenario: Scenario, params, testcase, run_logger):
		

		# Setup client
		client_cmd = ""
		client_proc = None
		if scenario.implementation.type == Type.DOCKER:
			client_cmd = (
				params
				+ " docker-compose up --abort-on-container-exit --timeout 1 "
				+ "client"
			)
			client_proc = subprocess.Popen(
				client_cmd,
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)

		elif scenario.implementation.type == Type.APPLICATION:
			client_cmd = scenario.implementation.command.format(origin=testcase.origin, cert_fingerprint=testcase.cert_fingerprint, request_urls=testcase.request_urls, client_log_dir=run_logger.client_log_dir_local, server_log_dir=run_logger.server_log_dir_local, shaper_log_dir=run_logger.shaper_log_dir_local)
			logging.debug("Vegvisir: running client: %s", client_cmd)
			client_proc = subprocess.Popen(
				client_cmd.split(' '),
				shell=False,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
			)
		logging.debug("Vegvisir: running client: %s", client_cmd)

		return client_proc

	# Runs the shaper docker container
	# Parameters
	#	Implementation of the server
	# 	(Run) Parameters for Docker 
	# Post
	#	Shaper is running
	# Returns
	#	Process running the container
	def run_shaper(self, implementation : Implementation, params):
		containers = "sim" #+ " ".join(testcase.additional_containers())

		cmd = (
			params
			+ " docker-compose up -d "	
			+ containers
		)
		
		proc = subprocess.run(
		cmd,
		shell=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT
		)

		return proc

	# Runs the server docker container
	# Parameters
	#	Implementation of the server
	# 	(Run) Parameters for Docker 
	# Post
	#	Server is running
	# Returns
	#	Process running the container
	def run_server(self, implementation : Implementation, params):
		containers = "server" #+ " ".join(testcase.additional_containers())

		cmd = (
			params
			+ " docker-compose up -d "
			+ containers
		)

		proc = subprocess.run(
		cmd,
		shell=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT
		)

		return proc 

	# Runs the additional containers of a testcase 
	# Parameters
	#	tescase 
	# 	(Run) Parameters for Docker 
	# Returns
	#	Process if there is a process that started containers
	# 	-1 if no process is started (because there are no additional containers specified)
	def run_additional_containers(self, testcase, params):

		# Only do something if additional containers list is not empty 
		if testcase.additional_containers:
			containers = " ".join(testcase.additional_containers())

			cmd = (
				params
				+ " docker-compose up -d "
				+ containers
			)

			proc = subprocess.run(
			cmd,
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT
			)

			return proc 

		return -1 


	# Adds server4 to the hosts file with hardcoded IP
	def _add_hosts_entry(self):
		#TODO create backup using -b and reset to backup instead of removing entry later
		hosts_proc = subprocess.Popen(
				# Hostman CLI provided by Python pyhostman package 
				["sudo", "-S", "hostman", "add", "193.167.100.100", "server4"],
				shell=False,
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
		out, err = hosts_proc.communicate(self.sudo_password.encode())
		logging.debug("Vegvisir: append entry to hosts: %s", out.decode('utf-8'))
		if not err is None:
			logging.debug("Vegvisir: appending entry to hosts file resulted in error: %s", err)

	# Removes server4 from the hosts file 
	def _remove_hosts_entry(self):
		hosts_proc = subprocess.Popen(
				# Hostman CLI provided by Python pyhostman package
				["sudo", "-S", "hostman", "remove", "--names=server4"],
				shell=False,
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT
			)
		out, err = hosts_proc.communicate(self.sudo_password.encode())
		logging.debug("Vegvisir: remove entry from hosts: %s", out.decode('utf-8'))
		if not err is None:
			logging.debug("Vegvisir: removing entry from hosts file resulted in error: %s", err)



	# Does all the setup, runs a single test with a given client, shaper server and testcase and then cleans up 
	# Outputs logs
	# Parameters
	#	client 		: client scenario (client implementation + parameters/configuration/settings)
	# 	shaper 		: shaper scenario (shaper implementation + parameters/configuration/settings)	
	# 	server		: server scenario (server implementation + parameters/configuration/settings)
	# 	testcase	: testcase 
	def run_test(self, client : Scenario, shaper : Scenario, server : Scenario, testcase):

		
		#################
		# Setup logging #
		#################

		run_parameters = self._get_run_parameters(testcase, server.implementation, shaper, client.implementation)

		if client.implementation.type == Type.APPLICATION:
			self._add_hosts_entry()


		result = TestResult()
		result.start_time = datetime.now()

		run_logger = RunLogger(self.sudo_password, True)

		# server curr image repo, name, tag
		# client curr image repo, name, tag
		# shaper curr image name
		# testcase.scenario.name, 
		# testcase.name
		self._start_time = datetime.now()
		self._test_label = ""
		self._log_dir = "logs/{}/{:%Y-%m-%dT%H:%M:%S}".format(self._test_label,self._start_time)
		log_dir = os.getcwd() + "/" + self._log_dir + "/"
		log_dir = log_dir + server.implementation.repo + "_" + server.implementation.name + "_" + server.implementation.tag + "_"
		if client.implementation.type == Type.DOCKER:
			log_dir = log_dir + client.implementation.repo + "_" + client.implementation.name + "_" + client.implementation.tag
		else:
			log_dir = log_dir + client.name 

		log_dir = log_dir + "/" + shaper.implementation.name + "_" + shaper.name + "/" + testcase.name

		# TODO fix more than 1 repetition
		# if self._test_repetitions > 1:
		# 	log_dir += '_run_' + str(self._curr_repetition)


		run_logger.create_log_locations(log_dir)


		###########################
		# Done setting up logging #
		###########################

		shaper_process = self.run_shaper(shaper.implementation, run_parameters)
		server_process = self.run_server(server.implementation, run_parameters) 
		additional_containers_process = self.run_additional_containers(testcase, run_parameters)


		# Wait for server and shaper to be ready
		# TODO: check if this can be replaced by something more resiliant
		sleep(2)

		# If client is NativeApplication we do network setup for it 
		if client.implementation.type == Type.APPLICATION:
			self._run_client_setup(client.implementation, run_logger)
			self._setup_network_for_test_application()

		client_process = self.run_client(client, run_parameters, testcase, run_logger)


		##########################################
		# Handle testcase (wait for end of test) #	
		##########################################

		# TODO: move to function

		try:
			if isinstance(testcase.testend, TestEndUntilDownload):
				testcase.testend.setup(client_process, log_dir + '/client', testcase.file_to_find, testcase.timeout_time)
			elif isinstance(testcase.testend, TestEndTimeout):
				testcase.testend.setup(client_process, testcase.timeout_time)
			else:
				testcase.testend.setup(client_process)
			testcase.testend.wait_for_end()
		except KeyboardInterrupt as e:
			logging.debug("Vegvisir: manual interrupt")


		##########################################
		# Done handling test case 				 #	
		##########################################

		# Docker output logs
		client_proc_stdout, _ = client_process.communicate()
		if client_proc_stdout != None:
			logging.debug("Vegvisir: client: %s", client_proc_stdout.decode("utf-8"))
		
		# Log output from processes running docker compose for server and shaper
		logging.debug("Vegvisir: shaper process: %s", shaper_process.stdout.decode("utf-8"))
		logging.debug("Vegvisir: server process: %s", server_process.stdout.decode("utf-8"))

		# If there are no additional containers function could have returned the integer -1, in this case we can't log
		try: 
			logging.debug("Vegvisir: additional containers process: %s", additional_containers_process.stdout.decode("utf-8"))
		except:
			pass
		
		proc = subprocess.run(
			run_parameters + " docker-compose logs -t",
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT
		)
		logging.debug("Vegvisir: %s", proc.stdout.decode("utf-8"))
		result.status = Status.SUCCES

		# Outputs logs and cleanup
		run_logger.save_logs(log_dir, testcase, run_parameters, client.implementation)
		run_logger.cleanup()

		self._shut_down_docker_containers(run_parameters)
		self._remove_hosts_entry()

		result.end_time = datetime.now()


		return result