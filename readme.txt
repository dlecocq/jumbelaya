0) First things first, you need:

- Python
- Chrome/Safari/Something that supports WebSockets

Well, that's pretty much all you need. If it's 2.6.1+, then you should probably be fine.

1) Start an http server.

	$> python -m SimpleHTTPServer 8888 > /dev/null &

2) Start the jumble server

	$) ./server

3) From browser, go to http://localhost:8888/
