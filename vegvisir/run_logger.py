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

from .implementation import Implementation, Role, Type, RunStatus, Command, DockerImplementation, NativeImplementation, Scenario, LogFileFormatter

# Class to handle the logging of a single run, for each run a new RunLogger is used.

class RunLogger:
	# TODO: set correct types and init values
	log_file = ""
	log_handler = ""
	client_log_dir = ""
	server_log_dir = ""
	shaper_log_dir = ""
	client_log_dir_local = ""
	server_log_dir_local = ""
	shaper_log_dir_local = ""
	_save_files = ""
	sudo_password = ""

	def __init__(self, sudo_password, save_files):
		self.sudo_password = sudo_password
		self._save_files = save_files
		self._setup_logging()

	# Create temporary directories to store logs and   
	def _setup_logging(self):
		#temporary shaper log
		self.shaper_log_dir = tempfile.TemporaryDirectory(dir="/tmp", prefix="logs_shaper_")
		
		# temporary server log
		self.server_log_dir = tempfile.TemporaryDirectory(dir="/tmp", prefix="logs_server_")
		
		# temporary client log
		self.client_log_dir = tempfile.TemporaryDirectory(dir="/tmp", prefix="logs_client_")
		
		# universal log
		self.log_file = tempfile.NamedTemporaryFile(dir="/tmp", prefix="output_log_")
		self.log_handler = logging.FileHandler(self.log_file.name)
		self.log_handler.setLevel(logging.DEBUG)	

		formatter = LogFileFormatter("%(asctime)s %(message)s")
		self.log_handler.setFormatter(formatter)
		logging.getLogger().addHandler(self.log_handler)
	
	def create_log_locations(self, path):
		self.client_log_dir_local = path + '/client'
		self.server_log_dir_local = path + '/server'
		self.shaper_log_dir_local = path + '/shaper'
		pathlib.Path(self.client_log_dir_local).mkdir(parents=True, exist_ok=True)
		pathlib.Path(self.server_log_dir_local).mkdir(parents=True, exist_ok=True)
		pathlib.Path(self.shaper_log_dir_local).mkdir(parents=True, exist_ok=True)

		

	# Copy logs from docker container (in /logs/ directory) to host file system
	# Parameters 
	#	container	: name of container to copy from 
	#	dir 		: directory to copy to 
	# 	params 		: parameters for the docker-compose 
	# Post
	#	Logs are copied 
	def _copy_docker_logs(self, container: str, dir: tempfile.TemporaryDirectory, params: str):
		r = subprocess.run(
			'docker cp "$('
			+ params + " "
			+ 'docker-compose --log-level ERROR ps -q '
			+ container
			+ ')":/logs/. '
			+ dir.name,
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
		)
		if r.returncode != 0:
			logging.info(
				"Copying logs from %s failed: %s", container, r.stdout.decode("utf-8")
			)


	# Logs kernel net parameters to output if debugging is enabled
	# TODO: better documentation
	def _log_kernel_net_parameters(self):
		# ip a
		net_proc = subprocess.Popen(
		["sudo", "-S", "ip", "a"],
		shell=False,
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT
		)

		out, err = net_proc.communicate(self.sudo_password.encode())
		logging.debug("Vegvisir: net log:\n%s", out.decode("utf-8"))
		if not err is None:
			logging.debug("Vegvisir: net log error: %s", err.decode("utf-8"))

		# sysctl -a 
		kernel_proc = subprocess.Popen(
			["sudo", "-S", "sysctl", "-a"],
			shell=False,
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT
		)

		out, err = kernel_proc.communicate(self.sudo_password.encode())
		logging.debug("Vegvisir: kernel log:\n%s", out.decode("utf-8"))
		if not err is None:
			logging.debug("Vegvisir: kernel log error: %s", err.decode("utf-8"))

	
	# Save (copy to) all the created in the output log directory
	def save_logs(self, path, testcase, run_parameters, client: Implementation):
		# copy logs from Docker
		self._copy_docker_logs("sim", self.shaper_log_dir, run_parameters)
		if client.type == Type.DOCKER:
			self._copy_docker_logs("client", self.client_log_dir, run_parameters)
		self._copy_docker_logs("server", self.server_log_dir, run_parameters)

		# save logs
		logging.getLogger().removeHandler(self.log_handler)
		self.log_handler.close()
		
		# TODO: re-add
		#if result.status == Status.FAILED or result.status == Status.SUCCES:
		if True:
			shutil.copytree(self.server_log_dir.name, self.server_log_dir_local, dirs_exist_ok=True)
			shutil.copytree(self.client_log_dir.name, self.client_log_dir_local, dirs_exist_ok=True)
			shutil.copytree(self.shaper_log_dir.name, self.shaper_log_dir_local, dirs_exist_ok=True)
			shutil.copyfile(self.log_file.name, path + "/output.txt")
			if self._save_files: #and result.status == Status.FAILED:
				#shutil.copytree(testcase.www_dir(), log_dir + "/www", dirs_exist_ok=True)
				try:
					shutil.copytree(testcase.download_dir(), path + "/downloads", dirs_exist_ok=True)
				except Exception as exception:
					logging.info("Could not copy downloaded files: %s", exception)
	
	# Clean up temporary log directories: self._client_log_dir, self._shaper_log_dir and self._server_log_dir
	# 
	#
	def cleanup(self):
		self.server_log_dir.cleanup()
		self.client_log_dir.cleanup()
		self.shaper_log_dir.cleanup()

