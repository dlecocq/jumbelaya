# We'll actually be using a lot more JSON
import json
# Sometimes we need to join words
from string import join
# This it the class from which we inherit
from server import Handler
# We need the game class that used to live here
from game import game
# We need the language class that used to live here
from language import language
# Inherit from the generalized client
from client import Client
# We need to make some url requests
import urllib2
# Import time for timing
import time

class JumbleClient(Client):
	# The graph API return this for users:
	# {
	# "id": "220439",
	# "name": "Bret Taylor",
	# "first_name": "Bret",
	# "last_name": "Taylor",
	# "link": "http://www.facebook.com/btaylor",
	# "gender": "male",
	# "locale": "en_US"
	# }
	
	def __init__(self, sock, info):
		super(JumbleClient, self).__init__(sock,info)
		# This is the oauth token we've received
		self.token  = ""
		# This is the client's information returned from facebook
		self.user   = {}
		# Time when last round was issued
		self.time   = None
		# The current game the user has
		self.game   = None
		# The user's current score
		self.score  = 0
		# Whether or not the user continues the game
		self.win    = False
		# The time limit between rounds (in seconds)
		self.timeLimit = 120
		# Facebook Graph API Base
		self.fbBase = "https://graph.facebook.com/me"
	
	def __repr__(self):
		s = super(JumbleClient, self).__repr__()
		# If our user list is populated, print that information
		if (len(self.user)):
			return s + '[' + self.user['name'] + ']'
		else:
			return s
	
	def __str__(self):
		return self.__repr__()
	
	def authenticate(self, token):
		# This method should take the given token,
		# store it, and then obtain information 
		# about the user based on it.
		# This should be a json object
		user_info = urllib2.urlopen(self.fbBase + "?access_token=" + token).read()
		self.log("Authenticated '" + user_info + "'")
		self.user = json.loads(user_info)
		if "error" in obj:
			self.user = {}
			return False
		else:
			return True
	
	def retrieveFromDB(self, id):
		# It's probably a good idea to ask for the user's
		# information early, and then verify we got the 
		# right info after FB authentication happens?
		# Regardless, we need this method
		return False
	
	def saveToDB(self, id):
		return False
	
	def markTime(self):
		self.time = time.time()
	
	def evaluate(self, words):
		# Mark the end time
		end = time.time()
		# For some reason, I'm not entirely sure of, we're encountering none games.
		if (self.game == None):
			self.log("None game encountered.")
			self.win = True
			return
		# Score the submission
		(score, win) = self.game.score(words)
		# If you submitted within the time limit
		# and you're marked as being able to continue
		if (end - self.time) < self.timeLimit:
			# If you're within the time limit, and you got
			# all anagrams last round, then add to score
			if self.win:
				self.score += score
			else:
				self.score  = score
		else:
			# Otherwise, reset the score, and mark whether
			# you continue or not
			self.score = score
		# Regardless of what happened, you can continue
		# if you got all the anagrams necessary
		self.win = win	

class Jumble(Handler):
	def __init__(self):
		# The games this server knows about
		self.languages = {}
		self.initializeLanguages(['english'])
		self.games     = {}
		
	def initializeLanguages(self, langs):
		for lang in langs:
			self.log("Initializing " + lang)
			self.languages[lang] = language(lang, [6])
	
	def connection(self, client):
		# Send languages
		self.sendLanguages(client)

	def message(self, client, obj):
		if ('newGame' in obj):
			self.newGame(client, obj)
		elif ('submitGame' in obj):
			self.submitGame(client, obj)
		elif ('errorReport' in obj):
			self.errorReport(client, obj)
		elif ('registration' in obj):
			self.registration(client, obj);
	
	def newGame(self, client, obj):
		self.log('Note : ' + repr(client) + ' requested a new game.')
		# The default number of letters is 6
		count    = 6 if ('size' not in obj) else obj['size']
		# The default language is english
		language = 'english' if ('language' not in obj) else obj['language']
		# If the requested language is supported, then return
		if language in self.languages:
			# Ask for a random game
			game = self.languages[language].getRandomGame(count)
			# Store the client's game
			client.game = game
			# Send the game to the client
			client.send(game.toGameString())
			# Ask the client to mark the time
			client.markTime()
		else:
			# This language is not supported
			self.log('Language "' + language + '" not supported')
			client.send(json.dumps({'error':'"' + language + '" not supported.'}))
	
	def submitGame(self, client, obj):
		# Get the submitted game
		sGame = obj['submitGame']
		# Ask the client to evaluate the submission
		client.evaluate(sGame['words'])
		if (game == None):
			# We've been getting some None game objects, not sure why.
			self.log("None game encountered.")
		else:
			# Get the client's game object
			game  = client.game
			# Log a brief message
			self.log("Client '" + repr(client) + "' guessed : " + join(sGame['words'], ","))
			# Construct an object to return to the client
			g = {'solution':{'id':game.id, 'word':game.word, 'total':len(game.words), 'words':game.words}, 'score':client.score, 'win':client.win}
			client.send(json.dumps(g, separators=(',',':')))
	
	def registration(self, client, obj):
		client.authenticate(obj['registration']['token'])
	
	def errorReport(self, client, obj):
		self.log("Client '" + repr(client) + "' reported the error: " + repr(obj))
	
	def sendLanguages(self, client):
		client.send(json.dumps({"languages" : [lang for lang in self.languages.keys()]}))
