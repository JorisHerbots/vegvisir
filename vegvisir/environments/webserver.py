from vegvisir.environments.base_environment import BaseEnvironment


class WebserverBasic(BaseEnvironment):
	def __init__(self) -> None:
		super().__init__()
		self.scenario = "servetest"
		self.set_QIR_compatability_testcase("http3")