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

	let show_json_qlog = false;
	let show_pcap = false;
	let show_other = false;
	let log_filters = document.getElementsByName('log_filter');
	log_filters.forEach(filter => {
		if (filter.checked) {
			if (filter.id === 'log_filter_json') {
				show_json_qlog = true;
			}
			if (filter.id === 'log_filter_pcap') {
				show_pcap = true;
			}
			if (filter.id === 'log_filter_other') {
				show_other = true;
			}
		}
	});
	let show_any_log = show_json_qlog || show_pcap || show_other;

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
					let show = false;
					let filename_parts = file.split('.');
					let ext = filename_parts[filename_parts.length - 1];

					if (['json', 'qlog'].includes(ext)) { if (show_json_qlog) { show = true; } }
					else if (['pcap'].includes(ext)) { if (show_pcap) { show = true; } }
					else if (show_other) { show = true; }

					if (show) {
						tds.push(new td(file, 1, [], path + node + '/' + file));
					}
				});
			}
			else {
				let rc = recursive_table(child, children[child], path + node + '/');
				if (rc !== undefined) {
					tds = tds.concat([rc]);
				}
			}
		}
		let max_depth = 0;
		tds.forEach(td => {
			max_depth += td.depth;
		});
		if (max_depth < 1) {
			max_depth = 1;
		}

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
							else if (show_any_log) {
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
let refresh_btn = document.createElement('button');
let refresh = function () {
	set_results(table);
};
refresh_btn.onclick = refresh;
refresh_btn.innerText = 'Refresh';
header.prepend(refresh_btn);

// Run
set_results(table);