# A rudimentary Ruby parser, which basically only understands assignment statements and literal
# expressions (and even then ignores many of the complexities, e.g. it only works on string
# literals that do not contain any expression substitutions).

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
				raise ValueError(f'input at index {i} does not match any pattern recognized by the lexer')

	return lex

KEYWORDS = (
	'BEGIN', 'END', 'alias', 'and', 'begin', 'break', 'case', 'class', 'def', 'defined', 'do',
	'else', 'elsif', 'end', 'ensure', 'false', 'for', 'if', 'in', 'module', 'next', 'nil', 'not',
	'or', 'redo', 'rescue', 'retry', 'return', 'self', 'super', 'then', 'true', 'undef', 'unless',
	'until', 'when', 'while', 'yield'
)

tokenize = lexer(
	(r'\s*', lambda: []),
	(r'#[^\n]*', lambda: []),
	(r'(::|=>|[\n;()\[\]{},\.=])', lambda m: [('operator', m)]),
	('|'.join(KEYWORDS), lambda m: [('keyword', m)]),
	(r'([A-Z_][a-zA-Z_0-9]*)', lambda m: [('constant', m)]),
	(r'([a-z_][a-zA-Z_0-9]*)', lambda m: [('identifier', m)]),
	(r'\$([a-zA-Z_][a-zA-Z_0-9]*)', lambda m: [('global-variable', m)]),
	(r'@([a-zA-Z_][a-zA-Z_0-9]*)', lambda m: [('instance-variable', m)]),
	(r':([a-zA-Z_]|[a-zA-Z_0-9]*)', lambda m: [('symbol', m)]),
	(r"'((?:[^']|\\')*')", lambda m: [('string-literal', m.replace("\\'", "'"))]),
	(r'"((?:[^"]|\\")*)"', lambda m: [('string-literal', m.replace('\\"', '"'))]),
)


		# integer literal
		m = re.match(r'\d+', src, i)

		if m is not None:
			yield 'integer-literal', m.group()
			i = m.end()

def parse_ruby(src):
	pass