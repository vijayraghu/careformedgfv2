import os
import sys
import requests
import json
from flask import Flask, request, Response, make_response, jsonify, url_for

#Initialize Flask app
app = Flask(__name__)

@app.route('/parse', methods=['POST'])
def parser():
	# Consume the entire email
	envelope = simplejson.loads(request.form.get(‘envelope’))
	
	# Get header information
	to_address = envelope[‘to’][0]
	from_address = envelope[‘from’]
	
	# Get information on body
	text = request.form.get(‘text’)
	html = request.form.get(‘html’)
	subject = request.form.get(‘subject’)
	
	# Process attachements, if any
	num_attachments = int(request.form.get(‘attachments’, 0))
	attachments = []
	if num_attachments > 0:
	for num in range(1, (num_attachments + 1)):
		attachment = request.files.get((‘attachment%d’ % num))
		attachments.append(attachment.read())
		
	return()
	
if __name__ == '__main__':
	app.run(host='0.0.0.0', debug = True)
