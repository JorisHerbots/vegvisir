import threading

from flask import (
    Blueprint, render_template, request
)
from flask.helpers import flash

from vegvisir.runner import (
	Runner
)

thread = None
mutex = threading.Lock()
returnvalue = None
errormsg = None

bp = Blueprint('docker', __name__, url_prefix='/docker')

runner = Runner(debug=True)

runner.set_implementations_from_file("implementations.json")

@bp.route('/', methods=['GET', 'POST'])
def docker_root():
	if mutex.locked():
		flash("Already working on a job!")
	elif request.method == 'POST':
		global returnvalue
		global errormsg

		def thread_func(func):
			global mutex
			global returnvalue
			mutex.acquire()
			returnvalue = func()
			mutex.release()

		def thread_func_1_arg(func, arg1):
			global mutex
			global returnvalue
			mutex.acquire()
			returnvalue = func(arg1)
			mutex.release()

		def thread_func_2_arg(func, arg1, arg2):
			global mutex
			global returnvalue
			mutex.acquire()
			returnvalue = func(arg1, arg2)
			mutex.release()

		action = request.form['action']
		if action == 'Update Images':
			thread = threading.Thread(target=thread_func, args=(runner.docker_update_images,))
			errormsg = "Failed to update images."

		elif action == 'Pull/Update Source Images':
			thread = threading.Thread(target=thread_func, args=(runner.docker_pull_source_images,))
			errormsg = "Failed to pull images."

		elif action == 'Save Imageset':
			thread = threading.Thread(target=thread_func_1_arg, args=(runner.docker_save_imageset,request.form['imageset']))
			errormsg = "Failed to save imageset {}.".format(request.form['imageset'])

		elif action == 'Load Imageset':
			thread = threading.Thread(target=thread_func_1_arg, args=(runner.docker_load_imageset,request.form['imageset']))
			errormsg = "Failed to load imageset {}.".format(request.form['imageset'])

		elif action == 'Create Imageset':
			thread = threading.Thread(target=thread_func_2_arg, args=(runner.docker_create_imageset,request.form['repo'],request.form['imageset']))
			errormsg = "Failed to create imageset {}/{}.".format(request.form['repo'],request.form['imageset'])

		elif action == 'Remove Imageset':
			thread = threading.Thread(target=thread_func_1_arg, args=(runner.docker_remove_imageset,request.form['imageset']))
			errormsg = "Failed to remove imageset {}.".format(request.form['imageset'])
			
		if not thread is None:
			thread.start()
			thread.join()
			if not errormsg is None and not returnvalue is None and not returnvalue == 0:
				flash(errormsg)
			else:
				flash("Successfully executed action: {}".format(action))
			runner.set_implementations_from_file("implementations.json")
			returnvalue = None
			errormsg = None
	return render_template('docker.html', loaded_sets=runner._image_sets)