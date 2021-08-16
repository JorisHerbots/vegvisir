import threading
from typing import List
from vegvisir.implementation import Implementation, RunStatus, Scenario, Shaper, Type
import time
from datetime import datetime

from flask import (
    Blueprint, render_template, request, flash, redirect, url_for
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

thread = None
mutex = threading.Lock()

@bp.route('/', methods=['GET'])
def root():
	return render_template('root.html', clients=clients, servers=servers, shapers=shapers, repos=runner._image_sets)

@bp.route('/run', methods=['POST'])
def run():
	global thread

	if mutex.locked():
		flash("Tests already running, did not start new tests")
	elif request.method == 'POST':
		mutex.acquire()
		runner._test_label = request.form['test_label']
		runner._test_repetitions = int(request.form['test_repetitions'])

		form = {}
		for x in request.form:
			y = x.split('@')
			if len(y) > 1 and not y[1].startswith('scenario.'):
				if not y[0] in form:
					form[y[0]] = []
				form[y[0]].append(request.form[x].split('@')[1])
			else:
				form[x] = request.form[x]

		for server in servers:
			if 'server.' + server.name in form:
				server.active = True
				for image in server.images:
					if image.url in form['server.' + server.name]:
						image.active = True
			else:
				server.active = False

		for client in clients:
			if 'client.' + client.name in form:
				client.active = True
				if client.type == Type.DOCKER:
					for image in client.images:
						if image.url in form['client.' + client.name]:
							image.active = True
			else:
				client.active = False

		for shaper in shapers:
			if 'shaper.' + shaper.name in form:
				shaper.active = True
				for image in shaper.images:
					if image.url in form['shaper.' + shaper.name]:
						image.active = True
			else:
				shaper.active = False

			for scenario in (x for x in request.form if x.startswith('shaper.' + shaper.name + '@scenario.')):
				for preset_scenario in shaper.scenarios:
					if  scenario == 'shaper.' + shaper.name + '@scenario.' + preset_scenario.name :
						preset_scenario.active = True
					elif request.form[scenario] != '':
						scenario_name = scenario.replace('shaper.' + shaper.name + '@scenario.', '')
						scen = Scenario(scenario_name, request.form[scenario])
						shaper.scenarios.append(scen)
		
		runner._servers = servers
		runner._clients = clients
		runner._shapers = shapers

		if "sudo_pass" in request.form:
			# TODO this might not work correctly?
			runner.set_sudo_password(request.form["sudo_pass"])

		def thread_func():
			global thread
			global mutex
			runner.run()
			thread = None
			mutex.release()

		thread = threading.Thread(target=thread_func)
		thread.start()
		time.sleep(3)

	return redirect(url_for('app.progress'))

@bp.route('/progress', methods=['GET'])
def progress():
	progress = {
		"nr_total": 0,
		"nr_waiting": 0,
		"nr_running": 0,
		"nr_done": 0,
		"client": None,
		"server": None,
		"shaper": None,
		"running": runner._running,
		"elapsed": ""
	}

	if runner._running:
		progress["elapsed"] = str(datetime.now() - runner._start_time)
	else:
		progress["elapsed"] = str(runner._end_time - runner._start_time)

	for x in runner._clients_active:
		progress["nr_total"] += 1
		if x.status == RunStatus.WAITING:
			progress["nr_waiting"] += 1
		elif x.status == RunStatus.RUNNING:
			progress["client"] = x
			progress["nr_running"] += 1
		elif x.status == RunStatus.DONE:
			progress["nr_done"] += 1
	
	for x in runner._servers_active:
		progress["nr_total"] += 1
		if x.status == RunStatus.WAITING:
			progress["nr_waiting"] += 1
		elif x.status == RunStatus.RUNNING:
			progress["server"] = x
			progress["nr_running"] += 1
		elif x.status == RunStatus.DONE:
			progress["nr_done"] += 1

	for x in runner._shapers_active:
		progress["nr_total"] += 1
		if x.status == RunStatus.WAITING:
			progress["nr_waiting"] += 1
		elif x.status == RunStatus.RUNNING:
			progress["shaper"] = x
			progress["nr_running"] += 1
		elif x.status == RunStatus.DONE:
			progress["nr_done"] += 1


	return render_template('progress.html', progress=progress)