#! /usr/bin/env python

# This is the code that will act as the session server
import socket
# Import our client classes
from jumble.client import Client, WSClient
# Import the server
from jumble.server import Server
# Import the server's handler, jumble
from jumble.jumble import Jumble, JumbleClient

j = Jumble()

s = Server(j, JumbleClient, 443)
s.start()
