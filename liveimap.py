#!/usr/bin/env python

# TODO readonly flag

import imaplib
import getpass
import lisp
from cStringIO import StringIO
import codecs
import niceimap
import sys
import os

def reconnect():
	previous_directory = connection.current_directory
	previous_directory_readonly = connection.current_directory_readonly
	connection.current_directory = None

	connection.__init__(connection.connection.host, connection.connection.port)
	#connection.open(connection.host, connection.port)
	connection.login(username, password)
	status, foo = connection.select(previous_directory, previous_directory_readonly)
	assert(status == "OK")
	

def reconnect_once(command):
	global connection
	global username
	global password # this is probably a security issue

	do_reconnect = False

	try:
		return command()
	except imaplib.IMAP4.abort, e:
		args = e.args
		if isinstance(args, tuple):
			if args[0] == 32: # unfortunately, that is not the default
				do_reconnect = True
			elif args[0].find("(32,") > -1: # 'Broken pipe')
				do_reconnect = True
			elif args[0].find("socket error: EOF") > -1:
				# /usr/lib64/python2.4/imaplib.py : self.abort('command: %s => %s' % (name, val))
				# imaplib.abort: command: LIST => socket error: EOF
				do_reconnect = True
			else:
				print >>sys.stderr, "reconnect_once: not reconnecting because", e.__class__, args
				raise
		else:
			print >>sys.stderr, "reconnect_once: not reconnecting because", e.__class, args
			raise
	except imaplib.IMAP4.error, e:
		args = e.args
		if isinstance(args, tuple):
			if args[0].endswith("illegal in state AUTH") or args[0].find("FETCH command received in invalid state.") > -1:
				do_reconnect = True
			else:
				print >>sys.stderr, "reconnect_once: not reconnecting because", e.__class__, args
				raise
		else:
			print >>sys.stderr, "reconnect_once: not reconnecting because", e.__class__, args
			raise

	assert(do_reconnect)

	# reconnect
	print >>sys.stderr, "reconnect_once: reconnecting because", e.__class__, args
	reconnect()

	return command()

	
host = os.environ["IMAPFS_IMAP_HOST"]
connection = niceimap.nice_IMAP(os.environ.get("IMAPFS_USE_SSL"), host, 993) # 143)

#connection.capabilities
#('IMAP4', 'IMAP4REV1', 'IDLE', 'LOGIN-REFERRALS', 'MAILBOX-REFERRALS', 'NAMESPACE', 'LITERAL+', 'UIDPLUS', 'CHILDREN', 'AUTH=NTLM')

#connection.authenticate("IMAP4")

username = os.environ.get("IMAPFS_USER") or getpass.getuser() # "danny.milosavljevic"
#print username

password = getpass.getpass("%s@%s password: " % (username, host))

#connection.login_cram_md5(username, password)
connection.login(username, password)

connection.select(readonly = True)

