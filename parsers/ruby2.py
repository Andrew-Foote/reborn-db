import re

def lexer(*patterns):
	patterns, callbacks = zip(*patterns)
	patterns = [re.compile(pattern, re.MULTILINE | re.DOTALL) for pattern in patterns]

	def lex(source):
		i = 0

		while i < len(source):
			for pattern, callback in zip(patterns, callbacks):
				m = pattern.match(source, i)

				if m is not None:
					yield from callback(*m.groups())
					i = m.end()
					break
			else:
				raise ValueError(f'input at index {i} does not match any pattern recognized by the lexer\n---\n({source[i:i + 25]}...)\n---')

	return lex

OPERATORS = ['=>', '=', '\\[', '\\]', '::', ',', '\\(', '\\)', '\\{', '\\}', '\\|\\|', '&&', '!', '\\.', '\\?', ':']

KEYWORDS = [
	'__ENCODING__', '__LINE__', '__FILE__', 'BEGIN', 'END', 'alias', 'and', 'begin', 'break',
	'case', 'class', 'def', 'defined?', 'do', 'else', 'elsif', 'end', 'ensure', 'false', 'for',
	'if', 'in', 'module', 'next', 'nil', 'not', 'or', 'redo', 'rescue', 'retry', 'return', 'self',
	'super', 'then', 'true', 'undef', 'unless', 'until', 'when', 'while', 'yield'
]

tokenize = lexer(
	(r'\n', lambda: [('newline',)]),
	(r'\s+', lambda: []),
	(r'#[^\n]*', lambda: []),
	(r'([a-zA-Z_][a-zA-Z_0-9]*[?!]?)', lambda m: [('keyword', m) if m in KEYWORDS else ('identifier', m)]),
	(r':([a-zA-Z_][a-zA-Z_0-9]*)', lambda m: [('symbol', m)]),
	(r'\$([a-zA-Z_][a-zA-Z_0-9]*)', lambda m: [('global-variable', m)]),
	('(' + '|'.join(OPERATORS) + ')', lambda m: [('operator', m)]),
	(r'(\d+)', lambda m: [('integer-literal', m)]),
	(r'"(.*?)"', lambda m: [('string-literal', m)]),
)

def parse_error(tokens, i, msg):
	raise ValueError(f'[{i}] {msg}; remaining input:\n' + ' '.join(map(str, tokens[i:i + 20])))

def parse(tokens):
	result, i = parse_statements(tokens, 0)

	if i != len(tokens):
		parse_error(tokens, i, 'expected no further input')

def parse_statements(tokens, i):
	print(i, tokens[i:i + 5], 'parse_statements')
	
	if i == len(tokens):
		return ('noop',), i
	
	statement, i = parse_statement(tokens, i)
	statements, i = parse_statements(tokens, i)
	return ('seq', statement, statements), i

def parse_statement(tokens, i):
	print(i, tokens[i:i + 5], 'parse_statement')

	if tokens[i][0] == 'newline':
		return parse_statements(tokens, i + 1)

	if tokens[i] == ('keyword', 'for'):
		if i + 1 == len(tokens) or not tokens[i + 1][0] == 'identifier':
			parse_error(tokens, i + 1, 'expected identifier after "for"')

		variable = tokens[i + 1][1]

		if i + 2 == len(tokens) or not tokens[i + 2] == ('keyword', 'in'):
			parse_error(tokens, i + 2, 'expected "in" after "for"')

		expression, i = parse_expression(tokens, i + 3)
		statements, i = parse_block_statements(tokens, i + 3)
		return ('for', variable, expression, statements), i

	if tokens[i] == ('keyword', 'begin'):
		begin_statements, i = parse_block_statements(tokens, i + 1, endword='rescue')
		rescue_statements, i = parse_block_statements(tokens, i)
		retuurn ('begin', begin_statements, rescue_statements), i

	if i + 1 < len(tokens) and tokens[i][0] == 'identifier' and tokens[i + 1] == ('operator', '='):
		variable = tokens[i][1]
		expression, i = parse_expression(tokens, i + 2)
		return ('=', variable, expression), i

	expression, i = parse_expression(tokens, i)
	return ('return', expression), i

def parse_block_statements(tokens, i, endwords=('end',)):
	print(i, tokens[i:i + 5], 'parse_block_statements')

	if i == len(tokens):
		parse_error(tokens, i, 'unterminated block')

	if tokens[i][0] == 'keyword' and tokens[i][1] in endwords:
		return ('noop',), i + 1
	
	statement, i = parse_statement(tokens, i)
	statements, i = parse_block_statements(tokens, i)
	return ('seq', statement, statements), i

def parse_expression(tokens, i):
	print(i, tokens[i:i + 5], 'parse_expression')

	expression, i = parse_atomic_expression(tokens, i)

	if i < len(tokens) and tokens[i] == ('operator', '::'):
		if not expression[0] == 'identifier':
			parse_error(tokens, i, 'expected identifier before "::"')

		if not (i < len(tokens) and tokens[i + 1][0] == 'identifier'):
			parse_error(tokens, i, 'expected identifier after "::"')

		return ('::', expression, tokens[i + 1][0]), i + 2

	if i < len(tokens) and tokens[i] == ('operator', '('):
		if not expression[0] == 'identifier':
			parse_error(tokens, i, 'expected identifer in function position')

		argument, i = parse_expression(tokens, i + 1)

		if not (i < len(tokens) and tokens[i] == ('operator', ')')):
			parse_error(tokens, i, 'expected ")" to close function call')

		return ('call', expression, argument), i + 1

	return expression, i

def parse_atomic_expression(tokens, i):
	print(i, tokens[i:i + 5], 'parse_atomic_expression')

	if i == len(tokens):
		parse_error(tokens, i, 'expected an expression')

	if tokens[i][0] == 'newline':
		return parse_expression(tokens, i + 1)

	# suspect this isn't how ruby's syntax really works, but it does the job
	if tokens[i] == ('identifier', 'proc'):
		return parse_proc(tokens, i + 1)

	if tokens[i][0] in ('identifier', 'symbol', 'integer-literal', 'string-literal'):
		return tokens[i], i + 1

	if tokens[i] == ('operator', '['):
		return parse_list_head(tokens, i + 1)

	if tokens[i] == ('operator', '{'):
		return parse_hash_head(tokens, i + 1)

	if tokens[i] == ('keyword', 'case'):
		subject, i = parse_expression(tokens, i + 1)
		clauses, i = parse_case_clauses(tokens, i)
		return ('case', subject, clauses), i

	parse_error(tokens, i, 'cannot parse expression')

def parse_list_head(tokens, i):
	print(i, tokens[i:i + 5], 'parse_list_head')

	if i == len(tokens):
		parse_error(tokens, i, 'unterminated list')

	if tokens[i][0] == 'newline':
		return parse_list_head(tokens, i + 1)

	if tokens[i] == ('operator', ']'):
		return ('empty-list',), i + 1

	item, i = parse_expression(tokens, i)
	items, i = parse_list_tail(tokens, i)
	return ('list-cons', item, items), i

def parse_list_tail(tokens, i):
	print(i, tokens[i:i + 5], 'parse_list_tail')

	if i == len(tokens):
		parse_error(tokens, i, 'unterminated list')

	if tokens[i][0] == 'newline':
		return parse_list_tail(tokens, i + 1)

	if tokens[i] == ('operator', ']'):
		return ('empty-list'), i + 1

	if tokens[i] == ('operator', ','):
		return parse_list_head(tokens, i + 1)

	parse_error(tokens, i, 'expected comma')

def parse_hash_head(tokens, i):
	print(i, tokens[i:i + 5], 'parse_hash_head')

	if i == len(tokens):
		parse_error(tokens, i, 'unterminated hash')

	if tokens[i][0] == 'newline':
		return parse_hash_head(tokens, i + 1)

	if tokens[i] == ('operator', '}'):
		return ('empty-hash',), i + 1

	key, i = parse_expression(tokens, i)

	if not (i < len(tokens) and tokens[i] == ('operator', '=>')):
		parse_error(tokens, i, 'expected "=>"')

	value, i = parse_expression(tokens, i + 1)
	items, i = parse_hash_tail(tokens, i)
	return ('hash-cons', (key, value), items), i

def parse_hash_tail(tokens, i):
	print(i, tokens[i:i + 5], 'parse_hash_tail')

	if i == len(tokens):
		parse_error(tokens, i, 'unterminated hash')

	if tokens[i][0] == 'newline':
		return parse_hash_tail(tokens, i + 1)

	if tokens[i] == ('operator', '}'):
		return ('empty-hash',), i + 1

	if tokens[i] == ('operator', ','):
		return parse_hash_head(tokens, i + 1)

	parse_error(tokens, i, 'expected comma')

def parse_proc(tokens, i):
	print(i, tokens[i:i + 5], 'parse_proc')

	if i == len(tokens):
		parse_error(tokens, i, 'unterminated proc')

	if not tokens[i] == ('operator', '{'):
		parse_error(tokens, i, 'expected "{" after "proc"')
	
	statement, i = parse_statement(tokens, i + 1)
	statements, i = parse_proc_statements(tokens, i)
	return ('proc', ('seq', statement, statements)), i

def parse_proc_statements(tokens, i):
	print(i, tokens[i:i + 5], 'parse_proc_statements')

	if i == len(tokens):
		parse_error(tokens, i, 'unterminated proc')

	if tokens[i] == ('operator', '}'):
		return ('noop',), i + 1
	
	statement, i = parse_statement(tokens, i)
	statements, i = parse_proc_statements(tokens, i)
	return ('seq', statement, statements), i

def parse_case_clauses(tokens, i):
	print(i, tokens[i:i + 5], 'parse_case_clauses')

	if i == len(tokens):
		parse_error(tokens, i, 'unterminated "case" expression')

	if tokens[i] == ('keyword', 'end'):
		return ('empty-case',), i + 1

	if tokens[i] == ('keyword', 'when'):
		tests, i = parse_case_tests(tokens, i + 1)
		statements, i = parse_block_statements(tokens, i, endwords=('end', 'when'))

REBORN_INSTALL_PATH = 'D:\\Program Files\\Reborn19-Win\\Pokemon Reborn\\'

with open(REBORN_INSTALL_PATH + 'Scripts\\MultipleForms.rb') as f:
	source = f.read()

tokens = list(tokenize(source))
print(tokens[:20])
# for, case, else, then, next, if, begin, in, when, rescue, elsif, end
print(parse(tokens))

