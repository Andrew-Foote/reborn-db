# another attempt at doing a ruby parser, i forgot that i've already tried this at least twice,
# and given up, but putting this here in case i do end up doing one eventually

def lexer(states):
	"""Returns a lexer built from the given dictionary.

	Each key in the dictionary should be the name of a state for the lexer. The corresponding 
	value specifies how the lexer acts while it is in this state. It should be a sequence of 
	2-tuples, each of whose first item is a pattern (compiled regex) and whose second item is a 
	callback. As the lexer processes its input string, it will check each pattern against the 
	slice of the string starting at the current index. If there is a match, it will call the 
	callback on the captured groups (so the callback should take as many arguments as there are
	capturing groups in the pattern, and it should expect those arguments to be strings). The 
	return value of the callback is  expected to be a 2-tuple. The first item will be used as a 
	stream of tokens to emit, and the second item will be used as the name of the state to 
	transition to.

	The initial state of the lexer will be None."""

	def lex(source):
		i = 0
		line_no = 0
		cur_line_start = 0
		state = None

		while i < len(source):
			for pattern, callback in states[state]:
				m = pattern.match(source, i)

				if m is not None:
					tokens, state = callback(*m.groups())
					yield from tokens
					i = m.end()
					full_match = m.group(0)

					try:
						cur_line_start = full_match.rindex('\n') + 1
					except ValueError:
						continue
					else:
						line_no += full_match.count('\n')

					break
			else:
				col_no = i - cur_line_start

				raise ValueError(
					f'input at line {col_no}, column {col_no} does not match any pattern '
					'recognized by the lexer\n'
					'---\n'
					f'{source[i:i + 25]}...\n'
					'---'
				)

	return lexer

# We are basing this mainly on:
# https://ruby-doc.org/docs/ruby-doc-bundle/Manual/man-1.4/syntax.html#lexical
# This is apparently for Ruby 1.4 (whereas RMXP reflects Ruby 1.8). But I can't find any other
# official documentation on Ruby's syntax. The Ruby language documentation seems to be pretty bad, 
# in general :(

RESERVED_WORDS = (
	'BEGIN', 'END', 'alias', 'and', 'begin', 'break', 'case', 'def', 'defined', 'do', 'else',
	'elsif', 'end', 'ensure', 'false', 'for', 'if', 'in', 'module', 'next', 'nil', 'not', 'or',
	'redo', 'rescue', 'retry', 'return', 'self', 'super', 'then', 'true', 'undef', 'unless',
	'until', 'when', 'while', 'yield'
)

def parse_simple_escape(char):
	return {
		't': '\t', 'n': '\n', 'r': '\r', 'f': '\f'
	}

@dataclass(frozen=True)
class NewlineToken:
	pass

WHITESPACE = re.compile(r'(?:[ \t\v]|\\[\n\r\f])+')
DOC_COMMENT = re.compile(r'[\n\r\f]+=begin.*?[\n\r\f]=end[^\r\n\f]*', re.S)
NEWLINE = r'[\n\r\f]+'
COMMENT = r'#[^\n\r\f]*'
RESERVED_WORD = r'({})'.format('|'.join(RESERVED_WORDS))
SEMICOLON = r';'
OPEN_BRACKET = r'\('
CLOSE_BRACKET = r'\)'
SQSTRING = r"'((?:[^'\\]|\\['\\])*)'"
BEGIN_DQSTRING = r'"'
SIMPLE_ESCAPE = r'\\([tnrfbaes])'
OCTAL_ESCAPE = r'\\([0-7]{3})'
HEX_ESCAPE = r'\\x([0-9a-fA-F]{2})'

# apparently there's also \cx, \C-x, \M-x, \M-\C-x, but the docs don't really describe what they 
# do---let's just hope they can be ignored
BEGIN_DOUBLE_QUOTED_STRING = r'"'

lex = lexer({
	None: [
		(WHITESPACE, lambda: ([], None)),
		(DOC_COMMENT, lambda: ([], None)),
		(NEWLINE, lambda: ([NewlineToken()], None)),
		(COMMENT, lambda: ([], None)),
		(RESERVED_WORD, lambda w: (ReservedWordToken(w), None)),
		(SEMICOLON, lambda: ([SemicolonToken()], None)),
		(OPEN_BRACKET, lambda: ([OpenBracketToken()], None)),
		(CLOSE_BRACKET, lambda: ([CloseBracketToken()], None)),
		(SINGLE_QUOTED_STRING_LITERAL, lambda s: ([StringLiteralToken(s)], None)),
		(BEGIN_DOUBLE_QUOTED_STRING_LITERAL, lambda: ([BeginStringLiteralToken()], 'dqstring'))
	],
	'dqstring': [
		(SIMPLE_ESCAPE)

		(TAB_ESCAPE, lambda: ([StringCharToken('\t')], 'dqstring')),
		(LF_ESCAPE, lambda: ([StringCharToken('\n')], 'dqstring')),
		(CR_ESCAPE, lambda: ([StringCharToken('\r')], 'dqstring')),
		(FF_ESCAPE, lambda: ([StringCharToken('\f')], 'dqstring')),
		(BACKSPACE_ESCAPE, lambda: ([StringCharToken('\f')], 'dqstring')),
	]

	(WHITESPACE, lambda: []),
	(DOC_COMMENT, lambda: []),
	(NEWLINE, lambda: [NewlineToken()]),
	(COMMENT, lambda: []),
	(RESERVED_WORD, lambda w: [ReservedWordToken(w)]),
	(DOUBLE_QUOTED_STRING, lambda s: [StringToken(s)]),
	(SINGLE_QUOTED_STRING, lambda s: [])

WHITESPACE = r'\s+'
PROC = r'proc\s*\{(.*?)\}' # fortunately none of the procs in the script have hash literals or blocks within them.
NUMBER = r'(-?\d+(?:\.\d+)?)'
STRING = r'("[^"]*")'
IDENTIFIER = r'[:\$]?([a-zA-Z_][a-zA-Z_0-9]*[?!]?)'
QUALIFIED_IDENTIFIER = IDENTIFIER + '::' + IDENTIFIER
KV_SEP = r'=>?|:'
SYMBOL = r'([\[\]{},])'

lex = lexer(
	(WHITESPACE, lambda: []),
	(DOC_COMMENT, lambda: []),
	(NEWLINE, lambda: [NewlineToken()])
	(COMMENT, lambda: []),
	(PROC, lambda v: [f'"{v}"']), # they don't have string literals within them either
	(NUMBER, lambda v: [f'"{v}"']), # sometimes they are used as keys, so put them as strings
	(STRING, lambda v: [v]),
	(QUALIFIED_IDENTIFIER, lambda u, v: [f'"{u}::{v}"']),
	(IDENTIFIER, lambda v: [f'"{v}"']),
	(KV_SEP, lambda: ':'),
	(SYMBOL, lambda v: v),
)