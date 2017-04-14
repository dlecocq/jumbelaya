# We need boto for talking to SimpleDB
import boto
from boto.sdb.connection import SDBConnection
# We need thread-safe tools
from collections import deque
# We need the game class
from game import game
# We need a random hash
import random
# We need it to be multithreaded
from threading import Thread, Semaphore

# Our SimpleDB credentials
access_key = "AKIAJQ7V6BGNHYW3FBBQ"
secret_key = "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"

class sdbCache():
	# How many entries can remain before we refresh
	threshold = 10

	def __init__(self, domain, selector, args = None, t = None):
		self.queue    = deque()
		self.domain   = domain
		self.conn     = None
		self.type     = t
		self.selector = selector
		self.args     = args
		# Only send one refresh request at a time
		self.sem      = Semaphore(1)
		self.refresh()
	
	def ensureConnected(self):
		# Add a test for whether or not the connection is valid
		if self.conn == None:
			self.conn = SDBConnection(access_key, secret_key)
	
	def blockingRefresh(self):
		try:
			self.ensureConnected()
			string = self.selector(self.args)
			print "Querying with '" + string + "'"
			rs = self.conn.select(self.domain, string)
			# If self.type is defined, we transform each element by it
			if self.type:
				self.queue.extend([self.type(r) for r in rs])
			else:
				self.queue.extend(rs)
		except boto.exception.SDBResponseError:
			print "Problem querying SimpleDB"
		# It is imperative that this semaphore be released appropriately
		self.sem.release()
	
	def refresh(self):
		if len(self.queue) < self.threshold:
			# If you can acquire the semaphore, get more!
			# Otherwise, just continue, more data is coming.
			if (self.sem.acquire(False)):
				Thread(target = self.blockingRefresh, args = ()).start()
	
	def pop(self):
		self.refresh()
		return self.queue.pop()
	
# A class that knows how to get puzzles from a language
class language():
	# By default, we should keep this many
	# games in our queue
	threshold = 10
	
	def __init__(self, name, which):
		# The name of the language
		self.name   = name
		# A hash of all the k-letter word games
		self.queues = {}
		for count in which:
			# Each of these should be a cache that makes a game
			self.queues[count] = sdbCache(self.name + "-" + repr(count), self.selector, {'count':repr(count)}, game.fromSimpleDB)
	
	def selector(self, args):
		return "select * from `english-" + args['count'] + "` where id < '" + self.randHash() + "' order by id desc limit 10"
	
	def randHash(self):
		return "%016x" % random.getrandbits(128)
	
	def getRandomGame(self, count):
		return self.queues[count].pop()
		
