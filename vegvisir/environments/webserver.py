from vegvisir.environments.base_environment import BaseEnvironment


class WebserverBasic(BaseEnvironment):
	def __init__(self) -> None:
		super().__init__()
		self.environment_name = "servetest"
		self.set_QIR_compatibility_testcase("http3")
