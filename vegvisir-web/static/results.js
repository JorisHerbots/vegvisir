async function set_results(table_div) {
	// clean table
	table_div.innerHTML = '';
	let table = document.createElement('table');
	table_div.appendChild(table);

	// get results
	let data = {};
	await fetch('/results.json')
		.then(response => response.json())
		.then(raw => { data = raw; });

	// set headers
	let hr = document.createElement('tr');
	data.headers.forEach(header => {
		let th = document.createElement('th');
		th.innerText = header;
		hr.appendChild(th);
	});
	table.appendChild(hr);

	class td {
		constructor(node, depth, children, path) {
			this.node = node;
			this.depth = depth;
			this.children = children;
			this.path = path;
			this.set = false;
		}
	};

	function recursive_table(node, children, path) {
		let tds = new Array();
		for (const child in children) {
			if (child == '/files') {
				children[child].forEach(file => {
					tds.push(new td(file, 1, [], path + node + '/' + file));
				});
			}
			else {
				tds = tds.concat([recursive_table(child, children[child], path + node + '/')]);
			}
		}
		let max_depth = 0;
		tds.forEach(td => {
			max_depth += td.depth;
		});
		return new td(node, max_depth, tds, path + node + '/');
	};

	let tds = recursive_table('', data.entries, 'logs');
	tds.children.forEach(entry => {
		let set_something = true;
		while (set_something) {
			set_something = false;
			let todo = [entry];
			let col = -1;
			let col_size = data.headers.length;
			let col_set = [];
			let depth_set = entry.depth;
			for (let index = 0; index < col_size; index++) {
				col_set.push(false)
			}
			let tr = document.createElement('tr');
			let patharray = new Array();

			function helper(nodes) {
				col++;
				nodes.forEach(node => {
					col_is_set = (col < col_size - 1) ? col_set[col] : col_set[col_size - 1];
					if (!node.set && !col_is_set && depth_set >= node.depth) {
						if (col < col_size - 1 || node.children.length == 0) {
							node.set = true;
							let col_to_set = (col < col_size - 1) ? col : col_size - 1;
							col_set[col_to_set] = true;
							set_something = true;
							depth_set = node.depth;

							let td = document.createElement('td');

							let linktext = patharray.join('/') + '/';
							if (col < col_size - 1) {
								let link = document.createElement('a');
								link.href = node.path;
								linktext += node.node;
								link.innerHTML = linktext;
								td.appendChild(link);
							}
							else {
								let button = document.createElement('button');
								button.innerHTML += linktext + '<b>' + node.node + '</b>';
								button.onclick = function () {
									let options = document.getElementsByName('result_viewer');
									let selected_option = undefined;
									options.forEach(opt => {
										if (opt.checked) {
											selected_option = opt;
										}
									});
									if (selected_option === undefined) {
										console.error('no selected viewer');
										return;
									}
									let link_to_open = selected_option.value;
									if (link_to_open === "open file") {
										link_to_open = window.location.origin + '/' + node.path;
									}
									else if (link_to_open === "custom url") {
										let url_input = document.getElementById('result_viewer_custom_url_text');
										link_to_open = url_input.value + window.location.origin + '/' + node.path;
									}
									else {
										link_to_open += window.location.origin + '/' + node.path;
									}
									window.open(link_to_open);
								};
								td.appendChild(button);
							}
							td.setAttribute('rowspan', node.depth);
							tr.appendChild(td);
						}
						else {
							patharray.push(node.node);
						}
					}
					if (node.children.length > 0) {
						helper(node.children);
					}
				});
				col--;
				patharray.pop();
			}

			helper(todo);

			if (set_something) {
				table.appendChild(tr);
			}
		}
	});
}

let header = document.getElementById('results_header');
let table = document.getElementById('results_table');

// setup header
let refresh = document.createElement('button');
refresh.onclick = function () {
	set_results(table);
}
refresh.innerText = 'Refresh';
header.prepend(refresh);

// Run
set_results(table);