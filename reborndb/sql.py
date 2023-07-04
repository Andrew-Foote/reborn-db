# dep of apsw_ext.py, can be deleted when that is deleted

def placeholders_table(data):
	rows = []

	for row in data:
		values = ', '.join('?' for _ in row)
		rows.append(f'({values})')

	return ',\n'.join(rows)
