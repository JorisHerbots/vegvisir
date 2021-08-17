async function set_results(table_div) {
	// clean table
	table_div.innerHTML = '';
	let table = document.createElement('table');
	table_div.appendChild(table);

	// get results
	let data = {};
	await fetch('/results.json')
		.then(response => response.json())
		.then(raw => { console.log(raw); data = raw; });

	// set headers
	let hr = document.createElement('tr');
	data.headers.forEach(header => {
		let th = document.createElement('th');
		th.innerText = header;
		hr.appendChild(th);
	});
	table.appendChild(hr);

	// set in table
	data.entries.forEach(entry => {
		let tr = document.createElement('tr');
		data.headers.forEach(header => {
			let td = document.createElement('td');
			if (header == 'logs') {
				td.innerText = entry['filename'];
			} else {
				td.innerText = entry[header];
			}
			tr.appendChild(td);
		});
		table.appendChild(tr);
	});
}

let header = document.getElementById('results_header');
let table = document.getElementById('results_table');

// setup header
let refresh = document.createElement('button')
refresh.onclick = set_results(table)
refresh.innerText = 'Refresh'
header.prepend(refresh)