# Parses the MultipleForms.rb script to obtain data on Pokémon form differences. Parsing a Ruby
# script in full generality is tricky, but this script is mostly just hases and arrays, so for this
# particular purpose we can get away with simply tokenizing it, ignoring any problematic parts, and
# converting the tokens to JSON.

import itertools as it
import json
import re

def lexer(*patterns):
	patterns, callbacks = zip(*patterns)
	patterns = [re.compile(pattern, re.DOTALL) for pattern in patterns]

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
				raise ValueError(f'input at index {i} does not match any pattern recognized by the lexer\n---\n{source[i:i + 25]}...\n---')

	return lex

WHITESPACE = r'\s+'
COMMENT = r'#[^\n]*'
PROC = r'proc\{(.*?)\}' # fortunately none of the procs in the script have hash literals or blocks within them.
NUMBER = r'(\d+(?:\.\d+)?)'
STRING = r'("[^"]*")'
IDENTIFIER = r'[:\$]?([a-zA-Z_][a-zA-Z_0-9]*[?!]?)'
QUALIFIED_IDENTIFIER = IDENTIFIER + '::' + IDENTIFIER
KV_SEP = r'=>?'
SYMBOL = r'([\[\]{},])'

tokenize = lexer(
	(WHITESPACE, lambda: []),
	(COMMENT, lambda: []),
	(PROC, lambda v: [f'"{v}"']), # they don't have string literals within them either
	(NUMBER, lambda v: [f'"{v}"']), # sometimes they are used as keys, so put them as strings
	(STRING, lambda v: [v]),
	(QUALIFIED_IDENTIFIER, lambda u, v: [f'"{u}::{v}"']),
	(IDENTIFIER, lambda v: [f'"{v}"']),
	(KV_SEP, lambda: ':'),
	(SYMBOL, lambda v: v),
)

def lex(source):
	source = re.search(r'\{.*\}', source, re.DOTALL).group() # remove anything outside of the main hash
	yield from tokenize(source)

def without_trailing_commas(tokens):
	tokens1, tokens2 = it.tee(tokens)
	next(tokens2)

	for token1, token2 in it.zip_longest(tokens1, tokens2):
		if not (token1 == ',' and token2 in (']', '}')):
			yield token1

REBORN_INSTALL_PATH = 'D:\\Program Files\\Reborn19-Win\\Pokemon Reborn\\'

def parse(script):
	with open(REBORN_INSTALL_PATH + 'Scripts\\' + script, encoding='utf-8') as f:
		source = f.read()

	tokens = without_trailing_commas(lex(source))
	source_json = ''.join(tokens)
	return json.loads(source_json, strict=False)
	