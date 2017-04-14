# This class is for discovering anagrams
class tree:
	def __init__(self, words, base = ""):
		# Whether or not this node represents a real word or not
		self.valid = False
		# All the words that share the same beginning
		self.children = {}
		self.count = 0
		if (type(words) == str):
			self.insert(words)
		else:
			for word in words:
				self.insert(word)
	
	def insert(self, word):
		if (len(word) == 0):
			self.valid = True
			return
		else:
			if word[0] not in self.children:
				self.children[word[0]] = tree(word[1:])
			else:
				self.children[word[0]].insert(word[1:])
		
	def __getitem__(self, index):
		return self.children[index]

	def search(self, word):
		word_hash = {}
		for i in word:
			if i in word_hash:
				word_hash[i] += 1
			else:
				word_hash[i] = 1
		return self.search_hash(word_hash)
	
	def search_hash(self, word, base = ''):
		results = []
		if (self.valid):
			results.append(base)
		# word should be a hash of how many of which letters are remaining
		for i in word:
			if word[i] > 0 and i in self.children:
				word[i] -= 1
				results.extend(self.children[i].search_hash(word, base + i))
				word[i] += 1
		self.count += len(results)
		return results
	
	def log(self, message):
		print message
