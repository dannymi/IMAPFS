#!/usr/bin/env python

# TODO readonly flag

import imaplib
import getpass
import lisp
from cStringIO import StringIO
import codecs
import sys
import errno
import re
import exceptions
import rfc822
import time
import gmtime
import timeout
import imapcodec

def from_internaldate(date):
		try:
			#print >>sys.stderr, "ndate", date
			date = rfc822.parsedate_tz(date)
			#print >>sys.stderr, "xdate", date, type(date)
			date = gmtime.mkgmtime(date)
			#print >>sys.stderr, "okdate", date
		except:
			date = 0 # None # (1970, 1, 1, 18, 16, 22, 0, 1, 0)

		return date

def pair(items):
		"""
		>>> pair([1,2,3,4])
		[(1,2),(3,4)]
		
		can still be optimized a LOT.
		"""
		result = []
		while len(items) > 0:
			key = items[0]
			#print "key", key
			value = items[1]
			items = items[2:]

			result.append((key, value))

		return result

def lisp_escaped_quoted_string(s):
	return "\"%s\"" % s.replace("\"", "\\\"")

def parse_attributes(text):
	stream = StringIO()
	stream.write(text)
	stream.seek(0)
	premonition_stream_1 = lisp.premonition_stream(stream)
	items = lisp.parse(premonition_stream_1)
	return items

def parse_flags(text):
	# text = '1848 (FLAGS (\Deleted) INTERNALDATE \"25-May-2007 17:08:58 +0200\" RFC822 )'
	attributes = parse_attributes(text)

	#>>> attributes[1]
	#[\FLAGS, [\Deleted], \INTERNALDATE, '25-May-2007 17:08:58 +0200', \RFC822]
	#>>> attributes[2] IndexError: list index out of range

	items = dict(pair(attributes[1]))
	return items

def parse_items(all_items, just_one_item_p = False):
	#re_items = re.compile(r"^([0-9][0-9]*) (.*)$")
	#match = re_items.match(items)
	#assert(match)
	#print >>sys.stderr,"group(1)", match.group(1), uid, type(uid)
	#assert(int(match.group(1)) == int(uid))
	#items = match.group(2)

	stream = StringIO()

	# all_items arbitrary item, literal, ... parts
	for items in all_items:
		if isinstance(items, str) and items.startswith("Some messages in the mailbox had previously been expunged and could not be returned"):
			# Some messages in the mailbox had previously been expunged and could not be returned. <type 'str'>

			pass
			#raise ParseError()

		if items is None: # ???
			# ('46 (ENVELOPE ("Wed, 11 Apr 2007 13:08:38 +0200" {35}', 'Neues "Local-Index-Service" Projekt') <type 'tuple'>

			print >>sys.stderr, "error: one item is None: all_items = ", all_items
			raise ParseError()

		if isinstance(items, tuple): # has literal parts
			#print >>sys.stderr, "tuple", items
			coalesced_result = ""
			is_literal = False
			for tuple_item in items:
				if not is_literal:
					i = tuple_item.rfind("{")
					if i > -1:
						tuple_item = tuple_item[ : i]
						is_literal = True
				else:
					# is_literal
					is_literal = False

					tuple_item = lisp_escaped_quoted_string(tuple_item)

				stream.write(tuple_item)
		else:
			stream.write(items)

	stream.seek(0)

	#import pickle
	#pickle.dump(stream.getvalue(), open('/tmp/save.p','w')) # FIXME

	#print >>sys.stderr, ">>>", stream.getvalue(), "<<<"

	premonition_stream_1 = lisp.premonition_stream(stream)
	#assert(premonition_stream_1.peek() == "(")
	#premonition_stream_1.consume()

	items = lisp.parse(premonition_stream_1)
	# items = [1, [\UID, 0807, \FLAGS, [\Seen], ...], 2, [\UID, 0808, \FLAGS, [\Seen], ...]]

	items = pair(items)
	# items = [(1, [\UID, 0807, \FLAGS, [\Seen], ...]), (2, [\UID, 0808, \FLAGS, [\Seen], ...], ...)]
	"""
		(ENVELOPE
			("Wed, 10 Jan 2007 18:16:22 +0200" "subject" (
				("Long, Name" NIL "Name.Long" "fabalabs.org")
			)
			(
				("Long, Name" NIL "Name.Long" "fabalabs.org")
			)
			(
				("Long, Name" NIL "Name.Long" "fabalabs.org")
			)
			(
				("Milosavljevic, Danny" NIL "Danny.Milosavljevic" "fabasoft.com")
				("Pesendorfer, Klaus" NIL "Klaus.Pesendorfer" "fabasoft.com")
				("Lechner, Jakob" NIL "Jakob.Lechner" "fabasoft.com")
			)
			NIL
			NIL
			NIL
			"<C2DF4DAA34CD0644A089964F6B55BBAD05387129@EVS-FABASOFT.fabagl.fabasoft.com>"))
	"""

	#items [\UID, \10525, \ENVELOPE, ['Wed, 10 Jan 2007 18:16:22 +0200', 'subject' ..

	#print >>sys.stderr, "items", items # [0]
	#assert(items[0][0] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"])
	#items.next()

	if not just_one_item_p:
		items = items[1 : ]

	for number, item in items:
		#print >>sys.stderr, "item", item
		#print >>sys.stderr, "yield", dict(pair(item)) # FIXME
		yield dict(pair(item))

def unescape_imap_name(text):
	return text.decode("imap4-utf-7")

def escape_imap_name(text):
	if not isinstance(text, unicode):
		text = text.decode("utf-8")

	return text.encode("imap4-utf-7")

def unescape_folder(folder):
	assert(folder.startswith("("))
	parts = folder.split(")", 1) # TODO can be nested.
	# "NIL"
	assert(len(parts) == 2)
	flags = parts[0][1:]
	rest = parts[1]

"""
input:
(\Marked \HasNoChildren) "/" "Public Folders/Fabasoft Consulting" <type 'str'>
(\Marked \HasChildren) "/" "Public Folders/Fabasoft Besprechungen" <type 'str'>
(\HasNoChildren) "/" "Public Folders/Fabasoft Training" <type 'str'>
(\Marked \HasNoChildren) "/" "Public Folders/Fabasoft Linux Schedule" <type 'str'>
(\HasNoChildren) "/" "Public Folders/Firmenautos Wien" <type 'str'>
(\Marked \HasNoChildren) "/" "Public Folders/Linux" <type 'str'>

result: yield (flags, separator, name)
"""
def decode_folders(folders):
	for folder_text in folders:
		#print "folder_text", folder_text
		stream = StringIO()
		stream.write(folder_text)
		# (\HasNoChildren) "/" "Gel&APY-schte Objekte" <type 'str'>
		stream.seek(0)
		premonition_stream_1 = lisp.premonition_stream(stream)
		assert(premonition_stream_1.peek() == "(")
		premonition_stream_1.consume()
		flags = lisp.parse(premonition_stream_1)

		assert(premonition_stream_1.peek() == " ")
		premonition_stream_1.consume()

		separator = lisp.parse_string_literal(premonition_stream_1)
		assert(separator == "/") # limitation

		assert(premonition_stream_1.peek() == " ")
		premonition_stream_1.consume()

		if premonition_stream_1.peek() == "\"":
			name = lisp.parse_string_literal(premonition_stream_1)
		else: # weird.
			name = premonition_stream_1.consume_rest()

		name = "".join(unescape_imap_name(name))

		#flags, separator, name = data
		yield flags, separator, name
		#else:
		#	print >>sys.stderr, "warning", "ignored line", data
	

class ParseError(exceptions.Exception):
	pass

class nice_IMAP(object):
	def __init__(self, use_SSL, *args, **kwargs):
		if use_SSL:
			self.connection = imaplib.IMAP4_SSL(*args, **kwargs)
		else:
			self.connection = imaplib.IMAP4(*args, **kwargs)
		
		self.current_directory = None
		self.current_directory_readonly = True
		self.current_uid_validity = None

	def flat_list(self, base):
		state, folders = self.connection.list(base)
		assert(state == "OK")
	
		if folders == [ None ]:
			# error?
			folders = []
		
		#print "F", folders
	
		folders = [x for x in decode_folders(folders)]
		for flags, separator, name in folders:
			if name.startswith(base):
				rest_name = name[len(base):]
				if rest_name != separator and base != "":
					continue
		
				if rest_name[1:].find("/")  > -1:
					continue
		
				yield name, flags # , separator

	def flat_list_simple(self, base):
		for name, flags in self.flat_list(base):
			yield name

	def get_message_uids(self):
		if self.current_directory_contents is not None:
			oldest_items_cachetime = min([items_cachetime for items_cachetime, items in self.current_directory_contents.values()])

			if time.time() - oldest_items_cachetime > timeout.timeout: # items too old.
				self.current_directory_contents = None
		
		#self.current_directory_contents = None # instead

		if self.current_directory_contents is not None:
			#print >>sys.stderr, "from cache", len(self.current_directory_contents)
			return self.current_directory_contents.keys()
			#[x[lisp.symbol("UID")] for x in self.current_directory_contents]
		else:
			print >>sys.stderr, "get_message_uids: live update"
			status, message_set = self.connection.uid("SEARCH", "ALL") # charset, criteria
			assert(status == "OK")
			message_set = message_set[0].split(" ")

			self.cache_directory_attributes() # so that it doesn't fetch live all the time

			if len(message_set) == 1 and message_set[0] == "":
				return []

			return message_set

	def get_mail_body(self, uid):
		import errno
		import exceptions

		status, items = self.connection.uid("FETCH", uid, '(FLAGS INTERNALDATE RFC822)')
		#print >>sys.stderr, "items", items

		text = items[0] 

		number_flags_date_syntax, body = text

		#print >>sys.stderr, ">>>%s<<<" % number_flags_date_syntax

		if number_flags_date_syntax.find(r"\Deleted") > -1: # speedup
			# "1848 (FLAGS (\Seen \Deleted) INTERNALDATE "25-May-2007 17:08:58 +0200" RFC822 {4118669}"
			flags_text = number_flags_date_syntax[ : number_flags_date_syntax.rfind("{")] + " \"\")" # replace body by something small

			print >>sys.stderr, "flags_text", flags_text

			items = parse_flags(flags_text)
			flags = items[lisp.symbol("FLAGS")]
			if lisp.symbol("Deleted") in flags:
				raise exceptions.IOError(errno.ENOENT, "No such file or directory 'uid#%s'" % uid)

		# ('47 (FLAGS (\\Seen) INTERNALDATE "11-Apr-2007 13:11:23 +0200" RFC822 {12482}', 
		#'X-MimeOLE: Produced By Microsoft Exchange V6.5\r\nReceived: by FABAMAIL.fabagl.fabasoft.com \r\n\tid <01C77C2A.23ACB406@FABAMAIL.fabagl.fabasoft.com>; 
		#print "---"
		#for item in items:
		return body

	def login(self, *args, **kwargs):
		self.connection.login(*args, **kwargs)
		
	def get_mail_envelope(self, uid): # SLOOOW
		#print >>sys.stderr, "get_mail_envelope UID", uid
		items = None
		if self.current_directory_contents is not None and uid in self.current_directory_contents:
			items_cachetime, items = self.current_directory_contents[uid] # [x for x in self.current_directory_contents if x[lisp.symbol("UID")] == uid]

			if time.time() - items_cachetime >= timeout.timeout: # too old
				items = None

		#items = None # FIXME

		for i in range(3):
			if items is None or items == []: # FIXME the latter is weird... and not necessary anymore
				status, items = self.connection.uid("FETCH", uid, '(UID ENVELOPE RFC822.SIZE FLAGS)')
				#f = file("/tmp/uid-%s" % uid, "w")
				#import pickle
				#pickle.dump(items, f) # FIXME FIXME
				#f.close()

				items = [x for x in parse_items(items, True)]
				if items == []: # weird, give it some time
					time.sleep(1)
				else:
					items = items[0]
					break

		if items == []: # not found
			raise exceptions.LookupError("message with UID %s not found in mailbox \"%s\"" % (uid, self.current_directory))

		#print >>sys.stderr, "items ENV", items
		uid = items[lisp.symbol("UID")]
		size = items[lisp.symbol("RFC822.SIZE")]
		envelope = items[lisp.symbol("ENVELOPE")]
		flags = items[lisp.symbol("FLAGS")]
		"""[
			'Wed, 10 Jan 2007 18:16:22 +0200', 
			'Some subject', 
			[['Long, Name', [], 'Silvio.Ziegelwanger', 'fabalabs.org']], 
			[['Long, Name', [], 'Long.Name', 'fabalabs.org']], 
			[['Long, Name', [], 'Long.Name', 'fabalabs.org']], 
			[['Milosavljevic, Danny', [], 'Danny.Milosavljevic', 'fabasoft.com'], ['Pesendorfer, Klaus', [], 'Klaus.Pesendorfer', 'fabasoft.com']],
			[],
			[],
			[],
			'<C2DF4DAA34CD0644A089964F6B55BBAD05387129@EVS-FABASOFT.fabagl.fabasoft.com>'
		]"""

		date, subject, from_, sender, reply_to, to_, cc, bcc, in_reply_to, message_id = envelope[:10]
		date = from_internaldate(date)

		return uid, flags, size, date, subject, from_, sender, reply_to, to_, cc, bcc, in_reply_to, message_id

	def select(self, mailbox = u"INBOX", readonly = None):
		if self.current_directory != mailbox or self.current_directory_readonly != readonly:
			#print >>sys.stderr, "really selecting", mailbox
			if mailbox != "":
				mailbox = escape_imap_name(mailbox)
				status, foo = self.connection.select(mailbox, readonly = readonly)
			else:
				status, foo = "OK", "0" # imaplib.IMAP4.select(self,  readonly = readonly)

			if status == "OK":
				self.current_directory = mailbox
				self.current_directory_readonly = readonly
				try:
					uidvalidity_raw = self.connection.response("UIDVALIDITY")
					self.current_uid_validity = int(uidvalidity_raw[1][0])
				except:
					self.current_uid_validity = None
					#print >>sys.stderr, "uidvalidity_raw weird", uidvalidity_raw # ("UIDVALIDITY", [None])

				try:
					self.cache_directory_attributes()
				except exceptions.Exception, e:
					print >>sys.stderr, "niceimap.cache_directory_attributes() failed because", e
					raise

			return status, foo
		else:
			return "OK", "TODO"

	def cache_directory_attributes(self):
		self.current_directory_contents = {} # uid -> [...]

		status, items = self.connection.uid("FETCH", "1:1000000000", "(UID FLAGS INTERNALDATE ENVELOPE RFC822.SIZE)")
		if status == "OK":
			if items == [None]:
				items = [] # ???

			#print >>sys.stderr, "cache_directory_attributes len items", len(items)

			self.current_directory_contents = {}
			for item in parse_items(items):
				uid = item[lisp.symbol("UID")]

				items_cachetime = time.time()
				self.current_directory_contents[uid] = items_cachetime, item
		else:
			self.current_directory_contents = None

	def chdir(self, path):
		status, foo = self.connection.select(path, readonly = True)
		if status != "OK":
			print exceptions.OSError(2, "No such file or directory: '%s'" % "a") # TODO more


	def unlink_message(self, uid):
		status, foo = self.connection.uid("STORE", uid, "+FLAGS", r"(\Deleted)")
		if status != "OK":
			raise exceptions.OSError(2, "No such file or directory: '%s'" % "a") # TODO more

if __name__ == "__main__":
	assert(parse_flags("1848 (FLAGS (\Deleted) INTERNALDATE \"25-May-2007 17:08:58 +0200\" RFC822 \"\")") == { lisp.symbol("FLAGS"): [lisp.symbol("Deleted")], lisp.symbol("INTERNALDATE"): "25-May-2007 17:08:58 +0200", lisp.symbol("RFC822"): "" })
