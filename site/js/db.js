function parseFrac(s) {
	const parts = s.split('/');
	if (parts.length === 1) parts = [parts[0], 1];
	return parts.map(BigInt);
}

function gcd(a, b) {
	while (b) [a, b] = [b, a % b];
	return a;
}

function reduceFrac(x) {
	const d = gcd(...x);

	// make sure x[1] and d have the same sign so the denominator is positive
	if ((x[1] < 0 && d > 0) || (x[1] > 0 && d < 0)) d = -d;
	
	return [x[0] / d, x[1] / d];
}

function formatFrac(x) {
	if (x[1] == 1) return x[0].toString();
	return x[0].toString() + '/' + x[1].toString();
}

async function setupDb() {
	// https://willschenk.com/articles/2021/sq_lite_in_the_browser/
	const SqlPromise = initSqlJs({
		locateFile: filename => `/js/thirdparty/${filename}`
	});

	const dataPromise = fetch('/db.sqlite').then(res => res.arrayBuffer());
	const [Sql, buf] = await Promise.all([SqlPromise, dataPromise]);
	const db = new Sql.Database(new Uint8Array(buf));
	window.db = db;

	// we need to add the frac collation

	db.create_function('frac_mul', (x, y) => {
		x = parseFrac(x); y = parseFrac(y);
		return formatFrac([x[0] * y[0], x[1] * y[1]]);
	});

	// const stmt = db.prepare('select name from pokemon order by number');
	// stmt.getAsObject();
	// stmt.bind();
	// while (stmt.step()) {
	// 	const row = stmt.getAsObject();
	// 	console.log(row);
	// }
}

export {setupDb};