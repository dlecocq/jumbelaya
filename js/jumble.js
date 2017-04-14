function jumble(host, verbose) {
	this.socket     = null;
	// The game in progress
	this.game       = null;
	// The anagrams that the user has correctly guessed
	this.correct    = [];
	// The anagrams that the user has incorrectly guess
	this.wrong      = [];
	// The host wo which we're connecting
	this.host       = host;
	// How talkative to be in logging messages
	this.verbose    = verbose;
	// When this current round started
	this.start      = null;
	// How much time a new game gets
	this.TIME       = 100;
	// Whether or not the user gets to continue to the next round
	this.win        = false;
	// Queued up messages to send
	this.messages   = [];
	// Our app id
	this.appId      = 103505226398249;
	// The current FB user's oauth token and expiry
	this.tokens     = null;
	// The timeout handle
	this.timeoutHandle  = null;
	// The interval handle
	this.intervalHandle = null;
	
	// User called-back handlers
	// When a new game is received from the server
	this.newGame          = null;
	// We've received the solution from the server
	this.gotSolution      = null;
	// We've got languages from the server
	this.gotLanguages     = null;
	// When a word is correctly guessed
	this.guessedCorrect   = null;
	// When a word is incorrectly guessed
	this.guessedWrong     = null;
	// When a word has already been guessed
	this.guessedAgain     = null;
	// A word has been guessed
	this.guessed          = null;
	// When the game is finished (solution reached, or time over)
	this.gameEnd          = null;
	// When the server sends the solution
	this.solutionReceived = null;
	// When the time remaining is updated
	this.timeUpdated      = null;
	// The browser is unsupported
	this.unsupported      = null;
	// Received an error message from the server
	this.errorReceived    = null;
	
	this.parse = function(message) {
		if (message.length == 0) {
			this.log("Received empty message.");
			return;
		}
		
		try {
			object = JSON.parse(message);
			// Check to see if there's a game defined in the message
			if ("game" in object) {
				// Make sure we're ready for a new game
				this.reset();
				
				// Set our game
				this.game = object.game;
				// Call the new game handler if it exists
				if (this.newGame) {
					this.newGame(this.game);
				}
	
				// You've got two minutes
				this.timeoutHandle  = window.setTimeout(function() { window.jumble.timeUp() }, 1000 * this.TIME);
				// For updating the clock if need be
				this.intervalHandle = window.setInterval(function() { window.jumble.timeUpdate() }, 1000);
				// Reset the game timer
				this.start = new stopwatch();
				this.start.start();
			} else if ("solution" in object) {
				if ("score" in object) {
					this.score = Number(object['score']);
				}
				// The game's solution has been received
				if (this.gotSolution) {
					this.gotSolution(object.solution);
				}
				this.reset();
			} else if ("languages" in object) {
				// We've received the list of supported languages
				if (this.gotLanguages) {
					this.gotLanguages(object.languages);
				}
			} else if ("registration" in object) {
				// This is registration confirmation. Should contain
				// information like their score, the number of letters
				// they have access to, etc.
				if (this.gotRegistration) {
					this.gotRegistration(object.registration);
				}
			} else if ("error" in object) {
				// The server sent us an error message.
				if (this.errorReceived) {
					this.errorReceived(object.error);
				}
			} else if ("request" in object) {
				if (object['request'] == 'newToken') {
					this.authenticate(true);
				}
			} else {
				this.log("Received message : " + message);
			}
		} catch (e) {
			this.log("JSON couldn't parse : " + message);
		}
	}
	
	this.authenticate = function(force) {
		hash = window.location.hash;
		// If the hash is empty... we need to authenticate
		if (hash.length == 0 || force) {
			// We don't want to get window.location per se,
			// as it might have hashes in it. So, we'll strip that out
			redirect = window.location.origin + window.location.pathname
			//redirect = "http://apps.facebook.com/jumbelaya/"
			url = "https://www.facebook.com/dialog/oauth?client_id=" + this.appId + "&redirect_uri=" + redirect + "&response_type=token";
			//window.open(url);
			//window.top.location.href = url;
		} else {
			hash = window.location.hash.replace('#', '').split("&");
			this.tokens = {};
			for (var i in hash) {
				term = hash[i].split('=');
				this.tokens[term[0]] = term[1];
			}
		}
	}
	
	this.upgrade = function() {
		window.top.location.href = 'http://www.facebook.com/dialog/pay?app_id=' + this.appId + '&redirect_uri=' + window.location + '&credits_purchase=true&order_info=1';
	}
	
	this.getLetters = function() {
		hash = {}
		letters = this.game.letters.split("");
		for(var i in letters) {
			if (letters[i] in hash) {
				hash[letters[i]] += 1;
			} else {
				hash[letters[i]] = 1;
			}
		}
		return hash;
	}
	
	this.timeUpdate = function() {
		remaining = this.TIME - this.start.time();
		// this.log(remaining + "s remaining");
		if (this.timeUpdated) {
			this.timeUpdated(remaining);
		}
	}		
	
	this.timeUp = function() {
		this.log("Time is up!");
		this.submitGame();
	}
	
	this.send = function(message) {
		if (this.socket.readyState != this.socket.OPEN) {
			// Queue up messages until it's connected
			this.messages.push(message);
			if (this.socket.readyState == this.socket.CLOSED) {
				this.connect(message);
			}
		} else {
			this.socket.send(message);
		}
	}
	
	this.connect = function() {
		// First, check to see if we have authenticated. If not,
		// then we must get a token.
		if (this.tokens == null) {
			this.authenticate();
			if (this.tokens == null) {
				return false;
			}
		} else if (this.tokens == "error") {
			// We must have tried authenticating, and it didn't work.
			this.log("We've had a problem authenticating.")
			return false;
		}
		
		try{
			this.socket = new WebSocket("ws://" + this.host);
			this.socket.jumble = this;

			// Set the WebSocket's callback handlers
			this.socket.onopen = function() {
				this.jumble.log("Connection opened to " + this.jumble.host);
				// Then we should send a registration message
				this.send(JSON.stringify({"registration":this.jumble.tokens}));
				while(this.jumble.messages.length) {
					m = this.jumble.messages.pop();
					this.jumble.log("Sending " + m)
					this.send(m);
				}
			};

			this.socket.onmessage = function(e) {
				this.jumble.parse(e.data);
		  };

			this.socket.onclose = function() {
				this.jumble.log("Connection to " + this.jumble.host + " closed.");
			};
		} catch(err) {
			if (this.unsupported) {
				this.unsupported();
			}
		}
		return true;
	}
	
	this.guess = function(word) {
		hash = MD5(word);
		// Check to see if it's already been guessed
		if (this.correct.indexOf(word) >= 0 || this.wrong.indexOf(word) >= 0) {
			if (this.guessedAgain) {
				this.guessedAgain(word);
			}
		} else if (this.game.words.indexOf(hash.substr(0,10)) != -1) {
			// Check to see if it's correct
			if (word.length == this.game.letters.length) {
				this.win = true;
			}
			this.correct.push(word);
			// If callback registered...
			if (this.guessedCorrect) {
				this.guessedCorrect(word);
			}
		} else {
			// Otherwise, it's wrong
			this.wrong.push(word);
			// If callback registered...
			if (this.guessedWrong) {
				this.guessedWrong(word);
			}
		}
		
		if (this.guessed) {
			this.guessed(word);
		}
		
		if (this.correct.length == this.game.total) {
			this.log("You got all the words!");
			this.submitGame();
		}
	}
	
	this.reset = function() {
		this.correct = [];
		this.wrong   = [];
		if (!this.win) {
			this.score = 0;
		}
		this.win     = false;
		this.game    = null;
		window.clearInterval(this.intervalHandle);
		window.clearTimeout(this.timeoutHandle);
	}
	
	// Methods that send information to the server
	this.requestNewGame = function(lang, size) {
		size = (size == null) ? 6 : size;
		lang = (lang == null) ? 'english' : lang;
		request = {'newGame':{'size':size, 'language':lang}};
		this.send(JSON.stringify(request));
	}
	
	this.submitGame = function() {
		if (this.gameEnd) {
			this.gameEnd(this.win);
		}
		request = {'submitGame':{'id':this.game.id,'words':this.correct}};
		this.send(JSON.stringify(request));
	}
	
	this.reportError = function(message) {
		obj = {'errorReport' : {'game' : this.game, 'correct' : this.correct, 'wrong' : this.wrong }, 'message' : message};
		this.send(JSON.stringify(obj));
	}
	
	this.initialize = function() {
		this.reset();
		this.connect();
		window.jumble = this;
	}
	
	this.log = function(message) {
		if (this.verbose) {
			window.console.log(message);			
		}
	}
	
	this.initialize();
}
