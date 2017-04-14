# We'll actually be using a lot more JSON
import json
# For logging messages
import time
# We need to return random games to the player
import random
# Sometimes we need to join words
from string import join
# We need a md5 hash
from hashlib import md5
# We need to group things
from itertools import groupby
# We need a boto exception
import boto

# This knows how to take a list of words, and make
# the game string that can be sent to the user,
# and knows how to parse solutions
class game():
	# Make a game object from a list of words
	@classmethod
	def fromWords(cls, word, words, cutoff=3):
		g = game()
		g.id = game.makeIDFromWord(word)
		g.word = word
		g.words = [w for w in words if len(w) >= cutoff]
		g.total = len(g.words)
		g.counts = (len(word) + 1) * [0]
		lengths = [len(word) for word in g.words]
		tuples = [(key, len(list(group))) for key, group in groupby(lengths)]
		for t in tuples:
			g.counts[t[0]] = t[1]
		return g
	
	# Make a game object from an oracle JSON object
	@classmethod
	def fromString(cls, string, cutoff=3):
		g = json.loads(string)
		return game.fromWords(g['word'], g['words'], cutoff)
	
	# Make a game object from a SimpleDB entry
	@classmethod
	def fromSimpleDB(cls, entry):
		g = game()
		g.id    = entry['id']
		g.words = entry['words']
		g.word  = entry['word']
		g.total = entry['length']
		g.json  = str(entry['json'])
		return g
	
	# Generate an ID for a word. This is abstracted because
	# we need a function that maps both "hello" and "oehll"
	# to the same ID, because essentially, they are the same game
	@classmethod
	def makeIDFromWord(cls, word):
		return game.makeHash(join(sorted([char for char in word]), ''))
	
	# Generate the hash however you want to, just make sure everyone
	# is using the same hash, by calling this function
	@classmethod
	def makeHash(cls, word):
		return md5(word).hexdigest()[0:10]

	def __init__(self):
		self.id         = ''
		self.words      = []
		self.word       = ''
		self.counts     = {}
		self.json       = None
		self.total      = 0
	
	def score(self, guesses):
		s = 0
		win = False
		for guess in guesses:
			if guess in self.words:
				# Exponential, with length 3 being 1 point
				s += 2 ** (len(guess) - 3)
				win = True if len(guess) == len(self.word) else win
		return (s, win)
	
	def scramble(self, string):
		# We split the string into an iterable, sample a random permutation
		# of the letters, and then join these with ''
		return join(random.sample([c for c in string], len(string)), '')
	
	def toOracleString(self):
		g = {}
		g['id'] = self.id
		g['word'] = self.word
		g['total'] = len(self.words)
		g['words'] = self.words
		return json.dumps(g, separators=(',',':'))
	
	def toGameString(self):
		if self.json == None:
			length = len(self.word)
			g = {}
			g['id'] = self.id
			g['letters'] = self.scramble(self.word)
			g['total'] = len(self.words)
			g['count'] = self.counts
			g['words'] = [game.makeHash(word) for word in self.words]
			self.json = json.dumps({'game' : g}, separators=(',',':'))
		return self.json
	
	def saveToSDB(self, dom):
		item = dom.new_item(self.id)
		item['id']     = self.id
		item['word']   = self.word
		item['length'] = len(self.word)
		item['json']   = self.toGameString()
		item['words']  = self.words
		item['rand']   = random.randint(100, 1000000)
		try:
			item.save()
			return True
		except boto.exception.SDBResponseError:
			print "Couldn't save " + self.id
			return False
