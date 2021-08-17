function set_results(table_div) {
	// clean table
	table_div.innerHTML = '';
	let table = document.createElement('table');
	table_div.appendChild(table);

	// get results
	let data = {
		headers: ['label', 'time', 'test', 'logs'],
		entries: []
	};

	// set headers
	let hr = document.createElement('tr');
	data.headers.forEach(header => {
		let th = document.createElement('th');
		th.innerText = header;
		hr.appendChild(th);
	});
	table.appendChild(hr);

	// set in table

}

let header = document.getElementById('results_header');
let table = document.getElementById('results_table');

// setup header
let refresh = document.createElement('button')
refresh.onclick = set_results(table)
refresh.innerText = 'Refresh'
header.prepend(refresh)