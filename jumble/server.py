#! /usr/bin/env python
#
# License will go here
#

'Server'

__name__      = 'Server'
__author__    = 'Dan Lecocq (dan.lecocq@kaust.edu.sa)'
__copyright__ = 'Copyright (C) 2010 Dan Lecocq'
__license__   = 'Undetermined'
__version__   = '0.1'

# We need the socket for communication
import socket
# We need multithreaded support
from threading import Thread, Semaphore
# For non-blocking reads with a large number of sockets
import select
# We'll actually be using a lot more JSON
import json
# For logging messages
import time
# We need to return random games to the player
import random

# We need the client module
from jumble.client import Client, ClientDisconnect

class Handler():
	def __init__(self):
		# For now, we have an empty handler
		print "Initializing handler"
	
	def connection(self, client):
		# We've received a new connection
		print "We've received a new connection from: " + repr(client)
	
	def message(self, client, obj):
		# We've received a message from a client
		print "We've received '" + repr(obj) + "' from: " + repr(client)
	
	def log(self, message):
		message = time.strftime('[%Y-%m-%d @ %H:%M:%S]') + ' ' + message.replace('\n', '\\n')
		print message

class Server():
	def __init__(self, handler, clientClass = Client, port = 8000):
		# For keeping track who's in what session
		self.sessions    = {}
		# For keeping track of I don't even know anymore
		self.members     = {}
		# The socket we'll be listening on
		self.sock        = None
		# The port we should be listening on
		self.port        = port
		# The file we'll use for logging
		self.logfile     = open('jumble.log', 'w+')
		# A semaphore for exclusive writing to the logfile
		self.ioSemaphore = Semaphore(1)
		# The number of connections we are currently hosting
		self.connections = 0
		# The handler we'll give non-server commands to
		self.handler     = handler
		# The client class to use
		self.clientClass = clientClass
		# It has to inherit from class
		if (not issubclass(clientClass, Client)):
			raise TypeError(repr(clientClass) + ' does not inherit from Client')
	
	def __del__(self):
		self.logfile.close()
	
	def removeMember(self, client):
		if self.members.has_key(client):
			session = self.members[client]
			self.members.pop(client)
			self.connections -= 1
			if self.sessions.has_key(session):
				try:
					self.sessions[session].remove(client)
					client.close()
					self.log('Client has left session \'%s\'' % session)
				except ValueError, err:
					self.log('Error: Client tried to leave session \'%s\' he\'s not in' % session)
		else:
			self.log('Internal Error: removeMember: Client not connected')
	
	def log(self, entry):
		# Thread-safe logging
		self.ioSemaphore.acquire()
		message = time.strftime('[%Y-%m-%d @ %H:%M:%S]') + ' ' + entry.replace('\n', '\\n')
		self.logfile.write(message + '\n')
		print message
		self.ioSemaphore.release()
	
	def acceptConnection(self, sock, info):
		try:
			c = self.clientClass(sock, info)
			self.log("Client @ %s connected. [%d]" % (repr(c), self.connections))
			self.members[c] = None
			self.connections += 1
			# Fire the handler's new connection event
			self.handler.connection(c)
		except ClientDisconnect as cd:
			self.log(cd)
	
	def listenForever(self):
		self.log('Starting listenForever')
		self.sock = socket.socket()
		self.sock.bind(('', self.port))
		self.sock.listen(1)
		while True:
			client, info = self.sock.accept()
			self.acceptConnection(client, info)
	
	def parseMessage(self, message, client):
		# For now I'm going to assume it's never going 
		# to receive malformed xml
		try:
			obj = json.loads(message)
			# Fire the handler's message event
			self.handler.message(client, obj)
		except ValueError:
			self.log('Error : ' + repr(client) + ' sent malformed JSON object : ' + message)
	
	def serveForever(self):
		self.log('Starting serveForever')
		while True:
			# I'm hoping that this will allow for a bugless
			# server.  Basically, the risk is if a lot of 
			# new connections form trough listenForever(), where
			# clients are added to self.unregistered while this
			# current call, which would then not contain a 
			# complete list of the clients to listen to.  Then,
			# the new connections that happen in this period will
			# experience the latency of min(timeout, time to first
			# communication among the rest of the clients).  So,
			# by making the timeout be something small but long
			# enough that it doesn't really poll the CPU too much.
			# It will only effect times that have recently be
			# registered.  This won't affect latency among already-
			# registered communication
			ins, outs, excs = select.select(self.members, [], self.members, 2)
			for s in ins:
				try:
					self.parseMessage(s.recv(), s)
				except ClientDisconnect, err:
					self.log('Client has disconnected')
					self.removeMember(s)
	
	def start(self):
		Thread(target = self.listenForever, args = ()).start()
		self.serveForever()
	
