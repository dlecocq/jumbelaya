#! /usr/bin/env python

# This is the structure we use for quick queries
from jumble.anagram import tree
# We need the game class for parsing
from jumble.game  import game
# Parse arguments
from optparse import OptionParser
# We need the SDB
import boto
from boto.sdb.connection import SDBConnection
# Random
import random

# Our SimpleDB credentials
access_key = "AKIAJQ7V6BGNHYW3FBBQ"
secret_key = "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"

def audit(words, num, language):
	cutoff = max(3, num - 4)
	count  = 0
	dbName = "%s-%d" % (language, num)
	domain = conn.get_domain(dbName)
	if not domain:
		domain = conn.create_domain(dbName)
	
	for word in words:
		# All anagrams longer than the cutoff
		results = [w for w in root.search(word) if len(w) >= cutoff]
		if (len(results) > 10 and len(results) < 30):
			results = sorted([(len(i), i) for i in results], reverse=True)
			results = [i[1] for i in results]
			print "Saving %s, with %d anagrams : %s" % (word, len(results), repr(results))
			if game.fromWords(word, results).saveToSDB(domain):
				count += 1
			else:
				print "Couldn't save " + word
		if count > 1000:
			break

parser = OptionParser()
parser.add_option('-d', '--dict', dest='dictionary', default='dictionaries/dictionary.txt', help='the dictionary file to use')
parser.add_option('-o', '--output', dest='output'  , default='output/', help='the folder to write the output to')

(options, args) = parser.parse_args()

print "Attempting to read from " + options.dictionary

try:
	f = file(options.dictionary)
	string = f.read().lower()
	words = string.split('\n')
	lengths = [6]
	conn = SDBConnection(access_key, secret_key)
	f.close()
except IOError:
	print "Cannot read file."
	exit()

print "Initializing tree..."
root = tree(string.split('\n'))
print "Ready to search!"

for length in lengths:
	tmp = [word for word in words if len(word) == length]
	tmp = random.sample(tmp, len(tmp))
	audit(tmp, length, "english")
