import dataclasses
from datetime import datetime
import getpass
import grp
import logging
import os
import pathlib
import queue
import shlex
import sys
import subprocess
import threading
import time
from typing import List, Tuple
import tempfile
import re
import shutil
from vegvisir.hostinterface import HostInterface
from vegvisir.configuration import Configuration
from vegvisir.data import VegvisirArguments
from vegvisir.environments.base_environment import BaseEnvironment
from vegvisir.exceptions import VegvisirException, VegvisirRunFailedException

from .implementation import Parameters, Endpoint

class LogFileFormatter(logging.Formatter):
	def format(self, record):
		msg = super(LogFileFormatter, self).format(record)
		# remove color control characters
		return re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]").sub("", msg)

class Experiment:
	def __init__(self, sudo_password: str, configuration_object: Configuration):
		self.configuration = configuration_object

		self.post_hook_processors: List[threading.Thread] = []
		self.post_hook_processor_request_stop: bool = False
		self.post_hook_processor_queue: queue.Queue = queue.Queue()  # contains tuples (method pointer, path dataclass)

		# self._sudo_password = sudo_password
		self.host_interface = HostInterface(sudo_password)
		# self._debug = debug

		self.logger = logging.getLogger("root.Experiment")
		# self.logger.setLevel(logging.DEBUG)
		# console = logging.StreamHandler(stream=sys.stderr)
		# if self._debug:
		# console.setLevel(logging.DEBUG)
		# else:
			# console.setLevel(logging.INFO)
		# self.logger.addHandler(console)

		# Explicit check so we don't keep trigger an auth lock
		if not self.host_interface._is_sudo_password_valid():
			raise VegvisirException("Authentication with sudo failed. Provided password is wrong?")

	# def set_sudo_password(self, sudo_password: str):
	# 	self._sudo_password = sudo_password

	# def spawn_subprocess(self, command: str, shell: bool = False) -> Tuple[str, str]:
	# 	if shell:
	# 		proc = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	# 	else:
	# 		shlex_command = shlex.split(command)
	# 		proc = subprocess.Popen(shlex_command, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
	# 	proc_input = self._sudo_password.encode() if "sudo" in command else None
	# 	if proc_input is not None:
	# 		out, err = proc.communicate(input=proc_input)
	# 	return out, err, proc

	# def spawn_parallel_subprocess(self, command: str, root_privileges: bool = False, shell: bool = False) -> subprocess.Popen:
	# 	shell = shell == True
	# 	if root_privileges:
	# 		# -Skp makes it so sudo reads input from stdin, invalidates the privileges granted after the command is ran and removes the password prompt
	# 		# Removing the password prompt and invalidating the sessions removes the complexity of having to check for the password prompt, we know it'll always be there
	# 		command = "sudo -Skp '' " + command
	# 	debug_command = command
	# 	command = shlex.split(command) if shell == False else command
	# 	proc = subprocess.Popen(command, shell=shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	# 	if root_privileges:
	# 		try:
	# 			proc.stdin.write(self._sudo_password.encode())
	# 		except BrokenPipeError:
	# 			logging.error(f"Pipe broke before we could provide sudo credentials. No sudo available? [{debug_command}]")
	# 	return proc

	# def spawn_blocking_subprocess(self, command: str, root_privileges: bool = False, shell: bool = False) -> Tuple[subprocess.Popen, str, str]:
	# 	proc = self.host_interface.spawn_parallel_subprocess(command, root_privileges, shell)
	# 	out, err = proc.communicate()
	# 	return proc, out.decode("utf-8").strip(), err.decode("utf-8").strip()

	# def _is_sudo_password_valid(self):
	# 	proc, _, _ = self.host_interface.spawn_blocking_subprocess("which sudo", True, False)
	# 	return proc.returncode == 0

	# def _scan_image_repos(self):
	# 	self._image_sets = []
	# 	proc = subprocess.run(
	# 		"docker images | awk '(NR>1) {print $1, $2}'",
	# 		shell=True,
	# 		stdout=subprocess.PIPE,
	# 		stderr=subprocess.STDOUT
	# 	)
	# 	local_images = proc.stdout.decode('utf-8').strip().replace(' ', ':').split('\n')
	# 	for img in local_images:
	# 		repo = get_repo_from_image(img)
	# 		if repo in self._image_repos:
	# 			tag = get_tag_from_image(img)
	# 			set_name = get_name_from_image(img)
	# 			if not repo + '/' + set_name in self._image_sets:
	# 				self._image_sets.append(repo + '/' + set_name)
	# 			for x in self._clients + self._servers + self.configuration.shapers:
	# 				if hasattr(x, 'image_name') and x.image_name == tag:
	# 					x.images.append(Image(img))

	def _post_hook_processor(self):
		while not self.post_hook_processor_request_stop:
			try:
				task, experiment_paths = self.post_hook_processor_queue.get(timeout=5)
				try:
					task(experiment_paths)
				except Exception as e:
					self.logger.error(f"Post-hook encountered an exception | {e}")
			except queue.Empty:
				pass  # We can ignore this one


	def _enable_ipv6(self):
		"""
		sudo modprobe ip6table_filter
		"""
		_, out, err = self.host_interface.spawn_blocking_subprocess("modprobe ip6table_filter", True, False)
		if out != "" or err != "":
			self.logger.debug(f"Enabling ipv6 resulted in non empty output | STDOUT [{out}] | STDERR [{err}]")

	def print_debug_information(self, command: str) -> None:
		_, out, err = self.host_interface.spawn_blocking_subprocess(command, True, False)
		self.logger.debug(f"Command [{command}]:\n{out}")
		if err is not None and len(err) > 0:
			self.logger.warning(f"Command [{command}] returned stderr output:\n{err}")

	def run(self):
		vegvisir_start_time = datetime.now()

		# Root path for logs needs to be known and exist for metadata copies
		self.configuration.path_collection.log_path_date = os.path.join(self.configuration.path_collection.log_path_root, "{:%Y-%m-%dT_%H-%M-%S}".format(vegvisir_start_time))
		pathlib.Path(self.configuration.path_collection.log_path_date).mkdir(parents=True, exist_ok=True)
		
		# Copy the implementations and experiment configurations for reproducibility purposes
		# For now, assume json files
		implementations_destination = os.path.join(self.configuration.path_collection.log_path_date, "implementations.json")
		experiment_destination = os.path.join(self.configuration.path_collection.log_path_date, "experiment.json")
		try:
			shutil.copy2(self.configuration.path_collection.implementations_configuration_file_path, implementations_destination) 
		except IOError as e:
			self.logger.warning(f"Could not copy over implementations configuration to root of experiment logs: {implementations_destination} | {e}")
		try:
			shutil.copy2(self.configuration.path_collection.experiment_configuration_file_path, experiment_destination) 
		except IOError as e:
			self.logger.warning(f"Could not copy over experiment configuration to root of experiment logs: {experiment_destination} | {e}")

		for _ in range(max(1, self.configuration.hook_processor_count)):
			processor = threading.Thread(target=self._post_hook_processor)
			processor.start()
			self.post_hook_processors.append(processor)

		self._enable_ipv6()

		experiment_permutation_total = len(self.configuration.shaper_configurations) * len(self.configuration.server_configurations) * len(self.configuration.client_configurations) * self.configuration.iterations
		experiment_permutation_counter = 0
		for shaper_config in self.configuration.shaper_configurations:
			for server_config in self.configuration.server_configurations:
				for client_config in self.configuration.client_configurations:
					yield client_config["name"], shaper_config["name"], server_config["name"], experiment_permutation_counter, experiment_permutation_total
					self.logger.info(f'Running {client_config["name"]} over {shaper_config["name"]} against {server_config["name"]}')
					shaper = self.configuration.shapers[shaper_config["name"]]
					server = self.configuration.server_endpoints[server_config["name"]]
					client = self.configuration.client_endpoints[client_config["name"]]

					# SETUP
					if client.type == Endpoint.Type.HOST:
						_, out, err = self.host_interface.spawn_blocking_subprocess("hostman add 193.167.100.100 server4", True, False)
						self.logger.debug("Vegvisir: append entry to hosts: %s", out.strip())
						if err is not None and len(err) > 0:
							self.logger.debug("Vegvisir: appending entry to hosts file resulted in error: %s", err)

					for run_number in range(0,self.configuration.iterations):
						# self._run_individual_test()
						iteration_start_time = datetime.now()
						
						# Paths, we create the folders so we can later bind them as docker volumes for direct logging output
						# Avoids docker "no space left on device" errors
						self.configuration.path_collection.log_path_iteration = os.path.join(self.configuration.path_collection.log_path_date, f"run_{run_number}/") if self.configuration.iterations > 1 else self.configuration.path_collection.log_path_date
						self.configuration.path_collection.log_path_permutation = os.path.join(self.configuration.path_collection.log_path_iteration, f"{client_config.get('log_name', client_config['name'])}__{shaper_config.get('log_name', shaper_config['name'])}__{server_config.get('log_name', server_config['name'])}")
						self.configuration.path_collection.log_path_client = os.path.join(self.configuration.path_collection.log_path_permutation, 'client')
						self.configuration.path_collection.log_path_server = os.path.join(self.configuration.path_collection.log_path_permutation, 'server')
						self.configuration.path_collection.log_path_shaper = os.path.join(self.configuration.path_collection.log_path_permutation, 'shaper')
						self.configuration.path_collection.download_path_client = os.path.join(self.configuration.path_collection.log_path_permutation, 'downloads')
						for log_dir in [self.configuration.path_collection.log_path_client, self.configuration.path_collection.log_path_server, self.configuration.path_collection.log_path_shaper, self.configuration.path_collection.download_path_client]:
							pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)
						pathlib.Path(os.path.join(self.configuration.path_collection.log_path_iteration, "client__shaper__server")).touch()						

						# We want all output to be saved to file for later evaluation/debugging
						log_file = os.path.join(self.configuration.path_collection.log_path_permutation, "output.txt")
						log_handler = logging.FileHandler(log_file)
						log_handler.setLevel(logging.DEBUG)
						self.logger.addHandler(log_handler)

						path_collection_copy = dataclasses.replace(self.configuration.path_collection)

						self.logger.debug("Calling environment pre_hook")
						pre_hook_start = datetime.now()
						try:
							self.configuration.environment.pre_run_hook(path_collection_copy)
							pre_hook_total = datetime.now() - pre_hook_start
							if pre_hook_total.total_seconds() > 5:
								self.logger.debug(f"Pre-hook took {datetime.now() - pre_hook_start} to complete.")
						except Exception as e:
							self.logger.error(f"Pre-hook encountered an exception | {e}")

						vegvisirBaseArguments = VegvisirArguments()
						vegvisirBaseArguments.LOG_PATH_CLIENT = self.configuration.path_collection.log_path_client
						vegvisirBaseArguments.LOG_PATH_SERVER = self.configuration.path_collection.log_path_server
						vegvisirBaseArguments.LOG_PATH_SHAPER = self.configuration.path_collection.log_path_shaper
						vegvisirBaseArguments.DOWNLOAD_PATH_CLIENT = self.configuration.path_collection.download_path_client

						client_image = client.image.full if client.type == Endpoint.Type.DOCKER else "none"  # Docker compose v2 requires an image name, can't default to blank string

						cert_path = tempfile.TemporaryDirectory(dir="/tmp", prefix="vegvisir_certs_")
						vegvisirBaseArguments.CERT_FINGERPRINT = self.configuration.environment.generate_cert_chain(cert_path.name)

						# TODO pick a better/cleaner spot to do this
						vegvisirBaseArguments.ORIGIN = "server4"
						vegvisirBaseArguments.ORIGIN_IPV4 = "server4"
						vegvisirBaseArguments.ORIGIN_IPV6 = "server6" # TODO hostman this
						vegvisirBaseArguments.ORIGIN_PORT = "443"
						vegvisirBaseArguments.WAITFORSERVER = "server4:443"
						vegvisirBaseArguments.SSLKEYLOGFILE = "/logs/keys.log"
						vegvisirBaseArguments.QLOGDIR = "/logs/qlog/"
						vegvisirBaseArguments.ENVIRONMENT = self.configuration.environment.environment_name if self.configuration.environment.environment_name != "" else None
						# vegvisirBaseArguments.SCENARIO = shaper.scenarios[shaper_config["scenario"]].command  # TODO jherbots Check if client and server need this?

						vegvisirServerArguments = dataclasses.replace(vegvisirBaseArguments, ROLE="server", TESTCASE=self.configuration.environment.get_QIR_compatibility_testcase(BaseEnvironment.Perspective.SERVER))
						vegvisirShaperArguments = dataclasses.replace(vegvisirBaseArguments, ROLE="shaper", SCENARIO = shaper.scenarios[shaper_config["scenario"]].command, WAITFORSERVER="server:443")  # Important edgecase! Shaper uses server instead of server4

						docker_compose_vars = (
							"CLIENT=" + client_image + " "
							"SERVER=" + server.image.full + " "
							"SHAPER=" + shaper.image.full + " "

							"CERTS=" + cert_path.name + " "
							"WWW=" + self.configuration.www_path + " "
							"DOWNLOAD_PATH_CLIENT=\"" + self.configuration.path_collection.download_path_client + "\" "

							"LOG_PATH_CLIENT=\"" + self.configuration.path_collection.log_path_client + "\" "
							"LOG_PATH_SERVER=\"" + self.configuration.path_collection.log_path_server + "\" "
							"LOG_PATH_SHAPER=\"" + self.configuration.path_collection.log_path_shaper + "\" "
						)

						
						# server_params = server.parameters.hydrate_with_arguments(server_config.get("arguments", {}), {"ROLE": "server", "SSLKEYLOGFILE": "/logs/keys.log", "QLOGDIR": "/logs/qlog/", "TESTCASE": self.configuration.environment.get_QIR_compatibility_testcase(BaseEnvironment.Perspective.SERVER)})
						server_params = server.parameters.hydrate_with_arguments(server_config.get("arguments", {}), vegvisirServerArguments.dict())
						# shaper_params = shaper.scenarios[shaper_config["scenario"]].parameters.hydrate_with_arguments(shaper_config.get("arguments", {}), {"WAITFORSERVER": "server:443", "SCENARIO": shaper.scenarios[shaper_config["scenario"]].command})
						shaper_params = shaper.scenarios[shaper_config["scenario"]].parameters.hydrate_with_arguments(shaper_config.get("arguments", {}), vegvisirShaperArguments.dict())
						
						with open("server.env", "w") as fp:
							Parameters.serialize_to_env_file(server_params, fp)
						with open("shaper.env", "w") as fp:
							Parameters.serialize_to_env_file(shaper_params, fp)

						# params += " ".join(testcase.additional_envs())
						# params += " ".join(shaper.additional_envs())
						# params += " ".join(server.additional_envs())
						# containers = "sim server " + " ".join(testcase.additional_containers())
						containers = "sim server"

						cmd = (
							docker_compose_vars
							+ " docker compose up -d "
							+ containers
						)
						# self.host_interface.spawn_parallel_subprocess(cmd, False, True)
						self.host_interface.spawn_blocking_subprocess(cmd, False, True) # TODO Test out if this truly fixes the RNETLINK error? This call might be too slow
						
						# Host applications require some packet rerouting to be able to reach docker containers
						if self.configuration.client_endpoints[client_config["name"]].type == Endpoint.Type.HOST:
							self.logger.debug("Detected local client, rerouting localhost traffic to 193.167.100.0/24 via 193.167.0.2")
							_, out, err = self.host_interface.spawn_blocking_subprocess("ip route del 193.167.100.0/24", True, False)
							if err is not None and len(err) > 0:
								raise VegvisirRunFailedException(f"Failed to remove route to 193.167.100.0/24 | STDOUT [{out}] | STDERR [{err}]")
							self.logger.debug("Removed docker compose route to 193.167.100.0/24")

							_, out, err = self.host_interface.spawn_blocking_subprocess("ip route add 193.167.100.0/24 via 193.167.0.2", True, False)
							if err is not None and len(err) > 0:
								raise VegvisirRunFailedException(f"Failed to reroute 193.167.100.0/24 via 193.167.0.2 | STDOUT [{out}] | STDERR [{err}]")
							self.logger.debug("Rerouted 193.167.100.0/24 via 193.167.0.2")

							_, out, err = self.host_interface.spawn_blocking_subprocess("./veth-checksum.sh", True, False)
							if err is not None and len(err) > 0:
								raise VegvisirRunFailedException(f"Virtual ethernet device checksum failed | STDOUT [{out}] | STDERR [{err}]")								

						# Log kernel/net parameters
						self.print_debug_information("ip address")
						self.print_debug_information("ip route list")
						self.print_debug_information("sysctl -a")
						self.print_debug_information("docker version")
						self.print_debug_information("docker compose version")

						# Setup client
						vegvisirClientArguments = dataclasses.replace(vegvisirBaseArguments, ROLE = "client", TESTCASE = self.configuration.environment.get_QIR_compatibility_testcase(BaseEnvironment.Perspective.CLIENT))
						client_params = client.parameters.hydrate_with_arguments(client_config.get("arguments", {}), vegvisirClientArguments.dict())
						
						client_cmd = ""
						client_proc = None
						if client.type == Endpoint.Type.DOCKER:
							with open("client.env", "w") as fp:
								Parameters.serialize_to_env_file(client_params, fp)
							
							# params += " ".join(client.additional_envs())
							client_cmd = (
								docker_compose_vars
								+ " docker compose up --abort-on-container-exit --timeout 1 "
								+ "client"
							)
							client_proc = self.host_interface.spawn_parallel_subprocess(client_cmd, False, True)

						elif client.type == Endpoint.Type.HOST:
							for constructor in client.construct:
								constructor_command = constructor.serialize_command(client_params)
								self.logger.debug(f"Issuing client construct command [{constructor_command}]")
								_, out, err = self.host_interface.spawn_blocking_subprocess(constructor_command, constructor.requires_root, True)
								if out is not None and len(out) > 0:
									self.logger.debug(f"Construct command STDOUT:\n{out}")
								if err is not None and len(err) > 0:
									self.logger.debug(f"Construct command STDERR:\n{err}")
							client_cmd = client.command.serialize_command(client_params)
							client_proc = self.host_interface.spawn_parallel_subprocess(client_cmd)
						self.logger.debug("Vegvisir: running client: %s", client_cmd)

						try:
							self.configuration.environment.start_sensors(client_proc, self.configuration.path_collection)
							self.configuration.environment.waitfor_sensors()
							self.configuration.environment.clean_and_reset_sensors()
						except KeyboardInterrupt:
							self.configuration.environment.forcestop_sensors()
							self.configuration.environment.clean_and_reset_sensors()
							with open(os.path.join(self.configuration.path_collection.log_path_permutation, "crashreport.txt"), "w") as fp:
								fp.write("Test aborted by user interaction.")
							self.logger.info("CTRL-C test interrupted")

						client_proc.terminate() # TODO redundant?
						if client.type == Endpoint.Type.HOST:
							# Doing this for docker will nullify the sensor system
							# Docker client logs are retrieved with "docker compose logs"
							out, err = client_proc.communicate()
							self.logger.debug(out.decode("utf-8"))
							self.logger.debug(err.decode("utf-8"))

						_, out, err = self.host_interface.spawn_blocking_subprocess(docker_compose_vars + " docker compose logs --timestamps server", False, True)
						self.logger.debug(out)
						self.logger.debug(err)
						_, out, err = self.host_interface.spawn_blocking_subprocess(docker_compose_vars + " docker compose logs --timestamps sim", False, True)
						self.logger.debug(out)
						self.logger.debug(err)
						_, out, err = self.host_interface.spawn_blocking_subprocess(docker_compose_vars + " docker compose logs --timestamps client", False, True)
						self.logger.debug(out)
						self.logger.debug(err)

						_, out ,err = self.host_interface.spawn_blocking_subprocess(docker_compose_vars + " docker compose down", False, True) # TODO TEMP
						self.logger.debug(out)

					# BREAKDOWN
					if client.type == Endpoint.Type.HOST:
						for destructor in client.destruct:
								destructor_command = destructor.serialize_command(client_params)
								self.logger.debug(f"Issuing client destruct command [{destructor_command}]")
								_, out, err = self.host_interface.spawn_blocking_subprocess(destructor_command, destructor.requires_root, True)
								if out is not None and len(out) > 0:
									self.logger.debug(f"Destruct command STDOUT:\n{out}")
								if err is not None and len(err) > 0:
									self.logger.debug(f"Destruct command STDERR:\n{err}")

						_, out, err = self.host_interface.spawn_blocking_subprocess("hostman remove --names=server4", True, False)
						self.logger.debug("Vegvisir: remove entry from hosts: %s", out.strip())
						if err is not None and len(err) > 0:
							self.logger.debug("Vegvisir: removing entry from hosts file resulted in error: %s", err)

					# Change ownership of docker output to running user
					try:
						real_username = getpass.getuser()
						real_primary_groupname = grp.getgrgid(os.getgid()).gr_name
						chown_to = f"{real_username}:{real_primary_groupname}"
						_, out, err = self.host_interface.spawn_blocking_subprocess(f"chown -R {chown_to} {self.configuration.path_collection.log_path_permutation}", True, False)
						if len(err) > 0:
							raise VegvisirException(err)
						self.logger.debug(f"Changed ownership of output logs to {chown_to} | {self.configuration.path_collection.log_path_permutation}")
					except (KeyError, TypeError):
						self.logger.warning(f"Could not change log output ownership @ {self.configuration.path_collection.log_path_permutation}, groupname might not be found?")
					except VegvisirException as e:
						self.logger.warning(f"Could not change log output ownership [{e}] @ {self.configuration.path_collection.log_path_permutation}")

					self.post_hook_processor_queue.put((self.configuration.environment.post_run_hook, path_collection_copy))  # Queue is infinite, should not block

					experiment_permutation_counter += 1

					if self.configuration.iterations > 1:
						self.logger.info(f'Test run {run_number}/{self.configuration.iterations} duration: {datetime.now() - iteration_start_time}')
					else:
						self.logger.info(f'Test run duration: {datetime.now() - iteration_start_time}')
					
					self.logger.removeHandler(log_handler)
					log_handler.close()
		
		yield None, None, None, None, None

		# Halt the hook processors
		wait_for_hook_processors_counter = 0
		while True:
			if self.post_hook_processor_queue.qsize() == 0:
				self.post_hook_processor_request_stop = True
			states = [t.is_alive() for t in self.post_hook_processors]
			time.sleep(5)
			if not any(states):
				for t in self.post_hook_processors:
					t.join()
				break
			if wait_for_hook_processors_counter % 2 == 0:
				hooks_todo = self.post_hook_processor_queue.qsize()
				if hooks_todo > 0:
					self.logger.info(f"Vegvisir is waiting for all post-hooks to process, approximately {self.post_hook_processor_queue.qsize()} request(s) still in queue.")
				else:
					self.logger.info(f"Vegvisir is waiting for {sum(states)} post-hook processor(s) to stop. If this message persists, perform CTRL + C")
			wait_for_hook_processors_counter += 1


	def _copy_logs(self, container: str, dir: tempfile.TemporaryDirectory, params: str):
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
