#! /usr/bin/python
#
# License will go here
#

'Client and WebSocket Client'

__name__      = 'client'
__author__    = 'Dan Lecocq (dan.lecocq@kaust.edu.sa)'
__copyright__ = 'Copyright (C) 2010 Dan Lecocq'
__license__   = 'Undetermined'
__version__   = '0.1'

# socket library for communication
import socket
# regular expressions for parsing out WS headers
import re
# struct for pack and unpack
from struct import pack, unpack
# Get md5
from hashlib import md5
# Import time
import time

# This is the client-has-disconnected exception
class ClientDisconnect(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

# This is the generalized client class for unlost
class RegClient:
	def __init__(self, sock, info):
		self.sock = sock
		self.info = info
	
	def __del__(self):
		self.close()
	
	def __repr__(self):
		return self.info[0] + ':' + repr(self.info[1])
	
	def __str__(self):
		return self.info[0] + ':' + repr(self.info[1])
	
	def close(self):
		self.sock.close()
	
	# Server sends message to the client
	def send(self, message):
		self.sock.send(message)
	
	# Returns a message the server should be receiving
	# from the client
	def recv(self):
		try:
			message = self.sock.recv(4096)
			if len(message):
				return [message]
			else:
				raise ClientDisconnect('Socket read nothing')
		except socket.error, msg:
			raise ClientDisconnect('Socket closed')
	
	# This is so that when we call it with select, then 
	# we can just pass in the object, instead of having
	# to know something about the implementation
	def fileno(self):
		return self.sock.fileno()
	
# This is the websocket-specific implementation, which
# inherits from the general client.
class WSClient(RegClient):
	# This is the websocket client received a malformed handshake
	class MalformedHeader(Exception):
		def __init__(self, value):
			self.value = value
		def __str__(self):
			return repr(self.value)
	
	def __init__(self, sock, info):
		self.sock = sock
		self.info = info
		# Stores the queued up messages
		self.messages = []
		handshake = self.sock.recv(4096)
		properties = {}
		for pair in handshake.split('\r\n'):
			# Debugging purposes
			# print "Found line " + pair
			m = re.search('^(\S+): (.+)$', pair)
			if (m != None):
				key, value = [m.group(1), m.group(2)]
				properties[key] = value.strip()
			else:
				# Debugging purposes
				# print "Working on line '" + pair + "' : " + repr(len(pair))
				if (len(pair) == 8):
					properties['key3'] = pair
				continue
		try:
			response = self.makeResponse(properties)
			self.sock.send(response)
			# Debugging purposes
			# print "Sent response : " + response
		except KeyError as key:
			self.sock.close()
			raise ClientDisconnect("Handshake: '" + handshake + "' did not contain '" + key[0] + "'")
		except WSClient.MalformedHeader as msg:
			self.sock.close()
			raise ClientDisconnect("Client received malformed header: '" + handshake + "' => " + msg)
	
	def makeResponse(self, properties):
		# Debugging purposes
		# print repr(properties)
		response = ""
		try:
			if ('Sec-WebSocket-Key1' not in properties):
				response = '''
HTTP/1.1 101 WebSocket Protocol Handshake\r
Upgrade: WebSocket\r
Connection: Upgrade\r
WebSocket-Origin: ''' + properties['Origin'] + '''\r
WebSocket-Location: ws://''' + properties['Host'] + '''/\r
WebSocket-Protocol: sample'''
				response = response.strip() + '\r\n\r\n'
			else:
				response = '''
HTTP/1.1 101 WebSocket Protocol Handshake\r
Upgrade: WebSocket\r
Connection: Upgrade\r
Sec-WebSocket-Origin: ''' + properties['Origin'] + '''\r
Sec-WebSocket-Location: ws://''' + properties['Host'] + '''/\r
Sec-WebSocket-Protocol: sample'''
				secKey = self.makeSecKey(properties['Sec-WebSocket-Key1'], properties['Sec-WebSocket-Key2'], properties['key3'])
				response = response.strip() + '\r\n\r\n' + secKey
		except ValueError, msg:
			print "Caught a value error : " + msg
			raise WSClient.MalformedHeader(repr(properties))
		return response
	
	def makeSecKey(self, key1, key2, key3):
		num1 = int(re.sub(r'\D', '', key1))
		num2 = int(re.sub(r'\D', '', key2))
		numSpaces1 = len(re.sub(r'[^ ]', '', key1))
		numSpaces2 = len(re.sub(r'[^ ]', '', key2))
		sec1 = num1 / numSpaces1
		sec2 = num2 / numSpaces2
		sec = pack('!I', sec1) + pack('!I', sec2) + key3
		sec = md5(sec).digest()
		return sec
	
	def send(self, message):
		self.sock.send('\x00' + message + '\xff')
	
	def recv(self):
		if (len(self.messages)):
			return self.messages.pop(0)
		try:
			# Get a message from the socket
			message = self.sock.recv(4096)
			if len(message):
				# Sometimes incomplete messages get read in. We will assume
				# that it's right there in the pipe
				while (message[-1] != '\xff'):
					message += self.sock.recv(4096)
				message = message.strip('\x00\xff')
				self.messages.extend(message.split('\xff\x00'))
				return self.messages.pop(0)
			else:
				raise ClientDisconnect('Socket read nothing')
		except socket.error, msg:
			raise ClientDisconnect('Socket error')

class Client(object):
	def __init__(self, sock, info):
		self.client = None
		if self.isWSClient(sock):
			self.client = WSClient(sock, info)
		else:
			self.client = RegClient(sock, info)
	
	def __repr__(self):
		return self.client.__repr__()
	
	def __str__(self):
		return self.client.__str__()
	
	def log(self, message):
		message = time.strftime('[%Y-%m-%d @ %H:%M:%S]') + ' ' + message.replace('\n', '\\n')
		print message
	
	def isWSClient(self, sock):
		message = sock.recv(4096, socket.MSG_PEEK);
		if message.find("GET") == 0:
			# If the first bit of the string is "GET"
			# then we're dealing with a WebSocket
			return True
		else:
			return False
	
	# Server sends message to the client
	def send(self, message):
		self.client.send(message)
	
	# Returns a message received from the client
	def recv(self):
		return self.client.recv()
	
	# This is so that when we call it with select, then 
	# we can just pass in the object, instead of having
	# to know something about the implementation
	def fileno(self):
		return self.client.fileno()
