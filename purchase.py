#! /usr/bin/env python
# Respond to the Facebook credits API

# Import CGI logging
import cgitb
# Import CGI capabilities
import cgi
# Import JSON for response
import json
# Import base64 for decoding fb_sig
import base64
# We need hashlib and hmac to compute the expected signature
import hmac, hashlib

appId = '103505226398249'
appSecret = 'e12bc48b61a4c76871446a021ea039f4'

def verifySignedRequest(signed_request):
	# Split by the period
	sig, payload = signed_request.split('.', 2)
	# Decode the messages
	sig  = base64.urlsafe_b64decode(sig)
	data = json.loads(base64.urlsafe_b64decode(payload))
	
	if ('algorithm' not in data or data['algorithm'].lower() != 'hmac-sha256'):
		# Bad algorithm
		return None
	else:
		expected = hmac.new(appSecret, msg=payload, digestmod=hashlib.sha256).digest()
	
	if sig != expected:
		# Boo!
		return None
	else:
		# Hooray!
		return data

# Enable CGI logging
cgitb.enable()
# Print the content type
print "Content-Type: text/plain;charset=utf-8"
print

data = cgi.FieldStorage()

# This should either be "payments_get_items" or "payments_status_update" 
method = data.getvalue('method', 'default')

if (method == "payments_get_items"):
	# First, make sure that the fb_sig parameter is valid
	if not verifySignedRequest(data.getvalue('fb_sig')):
		print json.dumps({'error':'Unable to verify signed request'})
	# Parse out order_info and other pertinent information
	# From what I can gather, order_info is basically just a product ID
	order_id   = data.getvalue('order_id')
	order_info = data.getvalue('order_info')
	# Based on this order_info, I should return some appropriate response:
	obj = {'content':[{\
	'title'       : 'Product title',
	'description' : 'Product description',
	'price'       : 3,
	'image_url'   : 'http://someurl',
	'product_url' : 'http://someurl',
	'method'      : 'payments_get_items',
	}]}
	# Give this response
	print json.dumps(obj)
elif (method == "payments_status_update"):
	# First, make sure that the fb_sig parameter is valid
	# if not verifySignedRequest(data.getvalue('fb_sig')):
	#	print json.dumps({'error':'Unable to verify signed request'})
	# This is when an order has done some more processing
	order_id      = data.getvalue('order_id')
	status        = data.getvalue('status')
	order_details = data.getvalue('order_details')
	# Now we need to respond with one of three statuses:
	# settled, canceled, or refunded
	print 'settled'
else:
	# Some bogus error.
	print json.dumps({'error':'Please provide either "payments_get_items" or "payments_status_update" as the method'})