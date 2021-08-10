from os import name
from typing import List
from vegvisir.implementation import Implementation, Scenario, Shaper

from flask import (
    Blueprint, render_template, request
)

from vegvisir.runner import (
	Runner
)

bp = Blueprint('app', __name__, url_prefix='/')

runner = Runner(debug=True)

runner.set_implementations_from_file("implementations.json")

clients: List[Implementation] = runner._clients
servers: List[Implementation] = runner._servers
shapers: List[Shaper] = runner._shapers

@bp.route('/', methods=['GET'])
def root():
	return render_template('root.html', clients=clients, servers=servers, shapers=shapers)

@bp.route('/run', methods=['POST'])
def run():
	if request.method == 'POST':
		for x in request.form:
			print(x, request.form[x])

		for server in servers:
			if 'server.' + server.name in request.form:
				server.active = True
			else:
				server.active = False

		for client in clients:
			if 'client.' + client.name in request.form:
				client.active = True
			else:
				client.active = False

		for shaper in shapers:
			if 'shaper.' + shaper.name in request.form:
				shaper.active = True
			else:
				shaper.active = False

			for scenario in (x for x in request.form if x.startswith('shaper.' + shaper.name + '@scenario.')):
				for preset_scenario in shaper.scenarios:
					if  scenario == 'shaper.' + shaper.name + '@scenario.' + preset_scenario.name :
						preset_scenario.active = True
					else:
						scen = Scenario(scenario, request.form[scenario])
						shaper.scenarios.append(scen)
		
		runner._servers = servers
		runner._clients = clients
		runner._shapers = shapers

		runner.run()

	return "running..."