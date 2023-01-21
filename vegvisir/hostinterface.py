import logging
import shlex
import subprocess
from typing import Tuple

class HostInterface:
	def __init__(self, sudo_password: str) -> None:
		self._sudo_password = sudo_password

	# def spawn_subprocess(self, command: str, shell: bool = False) -> Tuple[str, str]:
	#     if shell:
	#         proc = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	#     else:
	#         shlex_command = shlex.split(command)
	#         proc = subprocess.Popen(shlex_command, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
	#     proc_input = self._sudo_password.encode() if "sudo" in command else None
	#     if proc_input is not None:
	#         out, err = proc.communicate(input=proc_input)
	#     return out, err, proc

	def spawn_parallel_subprocess(self, command: str, root_privileges: bool = False, shell: bool = False) -> subprocess.Popen:
		shell = shell == True
		if root_privileges:
			# -Skp makes it so sudo reads input from stdin, invalidates the privileges granted after the command is ran and removes the password prompt
			# Removing the password prompt and invalidating the sessions removes the complexity of having to check for the password prompt, we know it'll always be there
			command = "sudo -Skp '' " + command
		debug_command = command
		command = shlex.split(command) if shell == False else command
		proc = subprocess.Popen(command, shell=shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		if root_privileges:
			try:
				proc.stdin.write(self._sudo_password.encode())
			except BrokenPipeError:
				logging.error(f"Pipe broke before we could provide sudo credentials. No sudo available? [{debug_command}]")
		return proc

	def spawn_blocking_subprocess(self, command: str, root_privileges: bool = False, shell: bool = False) -> Tuple[subprocess.Popen, str, str]:
		proc = self.spawn_parallel_subprocess(command, root_privileges, shell)
		out, err = proc.communicate()
		return proc, out.decode("utf-8").strip(), err.decode("utf-8").strip()

	def _is_sudo_password_valid(self):
		proc, _, _ = self.host_interface.spawn_blocking_subprocess("which sudo", True, False)
		return proc.returncode == 0
		