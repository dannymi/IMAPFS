#!/usr/bin/env python

# S-expressions

from cStringIO import StringIO
import exceptions

class premonition_stream(object):
	def __init__(self, stream):
		self.stream = stream
		self.pending = None

	def _fetch(self):
		if self.pending is None:
			self.pending = self.stream.read(1)
			if self.pending == "":
				self.pending = None

	def peek(self):
		self._fetch()
		return self.pending

	def consume(self):
		self.pending = None

	# for debugging and error messages:
	def consume_rest(self):
		rest = StringIO()
		if self.pending is not None:
			rest.write(self.pending)

		rest.write(self.stream.read())

		return rest.getvalue()

	def __iter__(self):
		while True:
			input = self.peek()
			if input is None:
				break

			yield input
			self.consume()

class a_symbol(object):
	def __init__(self, text):
		self.text = text

	def __repr__(self):
		return "\\%s" % self.text

symbols = {} # private

def symbol(text):
	global symbols
	result = symbols.get(text)
	if result is None:
		result = a_symbol(text)
		symbols[text] = result

	return result

NIL = symbol("NIL")
ENVELOPE = symbol("ENVELOPE")

def resolve(symbol_1):
	global NIL
	if symbol_1 == NIL:
		return []
	elif symbol_1 == ENVELOPE:
		return "ENVELOPE"
	else:
		raise exceptions.Exception("unknown symbol \"%s\"" % symbol_1)

def parse_string_literal(premonition_stream_1):
	assert(premonition_stream_1.peek() == "\"")

	premonition_stream_1.consume()
	
	literal = StringIO()
	in_escape = False
	for input in premonition_stream_1:
		if not in_escape:
			if input == "\\":
				in_escape = True
			elif input == "\"": # end quote.
				break
			else:
				literal.write(input)
		else:
			# TODO are there other escapes than "\"" possible?
			literal.write(input)
			in_escape = False
	
	item = literal.getvalue()
	assert(premonition_stream_1.peek() == "\"")
	premonition_stream_1.consume()

	return item

def parse_integer_literal(premonition_stream_1):
	input = premonition_stream_1.peek()
	assert(input in "0123456789")

	literal = StringIO()
	while input in "0123456789":
		literal.write(input)
		premonition_stream_1.consume()
		input = premonition_stream_1.peek()

	item = int(literal.getvalue())

	return item

def parse(premonition_stream_1):
	result = []

	input = premonition_stream_1.peek()
	while input not in [None]:
		if input == "(":
			premonition_stream_1.consume()
			item = parse(premonition_stream_1)
		elif input == ")":
			premonition_stream_1.consume()
			break
		elif input == "\"":
			item = parse_string_literal(premonition_stream_1)
		elif input == "\\":
			premonition_stream_1.consume()
			# symbol
			input = premonition_stream_1.peek()
			literal = StringIO()
			while (input not in [None, " ", "\t", ")"]):
				premonition_stream_1.consume()
	
				literal.write(input)
				input = premonition_stream_1.peek()
	
			item = symbol(literal.getvalue())
		#elif input == "{":
		#	item = parse_string_literal_2(premonition_stream_1)
		elif input in [" ", "\t"]:
			premonition_stream_1.consume()
			input = premonition_stream_1.peek()
			continue
		else: # printable char
			input = premonition_stream_1.peek()
			literal = StringIO()
			while (input not in [None, " ", "\t", ")"]):
				premonition_stream_1.consume()

				literal.write(input)

				input = premonition_stream_1.peek()

			#item = resolve(symbol(literal.getvalue()))

			literal = literal.getvalue()

			if len(literal) > 0 and literal[0] >= '0' and literal[0] <= '9':
				item = int(literal) # FIXME double? E? # FIXME: ValueError: invalid literal for int(): 5-Mar-2007
			else:
				item = symbol(literal)
		#else:
		#	raise exceptions.SyntaxError("syntax error near \"%s\"" % input)

		result.append(item)

		input = premonition_stream_1.peek()

	return result

# NIL
# newline?

def test(text):
		stream_1 = StringIO()
		stream_1.write(text)
		stream_1.seek(0)

		return parse(premonition_stream(stream_1))

def test_2():
	import pickle
	s = pickle.load(open("lisp-test.p", "rb"))
	result = test(s)
	return result

if __name__ == "__main__":
	assert(test("") == [])
	assert(test("()") == [[]])
	assert(test("\"hello\"") == ["hello"])
	assert(test("\"hello\" \"list\"") == ["hello", "list"])
	assert(test("NIL") == [symbol("NIL")])

	assert(test(r"\NewSymbol") == [ symbol("NewSymbol") ] )
	assert(test(r"(\NewSymbol)") == [ [ symbol("NewSymbol") ] ] )
	assert(test('(\NewSymbol) "/" ') == [ [ symbol("NewSymbol") ], "/" ] )

	assert(test(r'(\HasNoChildren) "/" "Gel&APY-schte Objekte"') == [[symbol("HasNoChildren")], "/", "Gel&APY-schte Objekte"])

	#print test("({10}\r\nhellohello") # now in imaplib


	test_2()

