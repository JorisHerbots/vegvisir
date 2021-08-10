from typing import List
from vegvisir.implementation import Implementation, Shaper

from flask import (
    Blueprint, render_template
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