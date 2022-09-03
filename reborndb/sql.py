def placeholders_table(data):
	rows = []

	for row in data:
		values = ', '.join('?' for _ in row)
		rows.append(f'({values})')

	return ',\n'.join(rows)
