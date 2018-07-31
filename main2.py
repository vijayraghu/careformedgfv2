# -*- coding: utf-8 -*-
import os
import sys
import urllib
import requests
import json
from flask import Flask, request, Response, make_response, jsonify, url_for
from contextlib import closing
# Twilio Helper Library
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Dial
# Google Text To Speech SDK
from google.oauth2 import service_account
from google.cloud import texttospeech_v1beta1 as texttospeech
# Dialogflow V2 SDK
import dialogflow
import re
import datetime

#####
##### Declare Global variables
#####
# Setting Google ID - Read env data
project_id = os.environ["DIALOGFLOW_PROJECT_ID"]
#Setting Google authorization credentials -  Read env data
credentials_dgf = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
#apiai_url = "https://api.api.ai/v1/query"
#apiai_querystring = {"v": "20150910"}

# Setup hints (speech contexts) for better speech recognition
hints = "1,2,3,4,5,6,7,8,9,0, 1 one first, 2 two second, 3 three third, 4 four fourth, 5 five fifth, 6 six sixth, 7 seven seventh, 8 eight eighth,9 nine ninth, 10 ten tenth, 0 zero o, account acount akount, mobile, roaming, top up topup,channels channel,tv TV, broadband broad band, fetch, extension, iphone, cable, recharge, recharging, optus Optus, Hey, EPL, English premier league, streaming, premier league"

app = Flask(__name__)

# Receive call from Twilio with paramters
@app.route('/welcome', methods=['GET','POST'])
def welcome():
	cli = request.values.get('From')
	call_id = request.values.get('CallSid')
	asr_lang = request.values.get('asr_lang', 'en-AU')
	lang_code = request.values.get('lang_code', 'en')
	hostname = request.url_root
	
	# Check for HOOP (hours of operations)
	start = datetime.time(0, 00)
	end = datetime.time(23, 59)
	timestamp = datetime.datetime.now().time()
	resp = VoiceResponse()
	
	if (end <= timestamp >= start):
		# If call time not within hours of operation, play appropriate prompt and transfer to general line
		values = {"text": 'Hi! The Care For me team is currently closed, the team is opened from 8:30 till 6 P M weekdays, please hold and I’ll transfer your call to the General Customer Service Number.'}
		print 'In start: before Google TTS'
		resp.play(hostname + 'goog_text2speech?' + qs)
		print 'In start: after Google TTS'
		resp.dial('+61280490603')
		return str(resp)
		
	else:
		# If call within office hours, triggering Dialogflow "Welcome" event
		
		#Setting credentials -  Read env data
		credentials_dgf = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
	
		#Setting Google Dialogflow Credentials and invoking SDK
		service_account_info = json.loads(credentials_dgf)
		credentials = service_account.Credentials.from_service_account_info(service_account_info)
		session_client = dialogflow.SessionsClient(credentials=credentials)
		session = session_client.session_path(project_id, call_id)
		event_input = dialogflow.types.EventInput(name=Welcome, language_code=lang_code)
		response = session_client.detect_intent(session=session, event_input=event_input)
		print response.text		
		output = json.loads(response.text)
		print output
		output_text = output['queryResult']['fulfillmentText']
		output_text = output_text.decode('utf-8')
		'''
		headers = {'authorization': 'Bearer ' + apiai_client_access_key, 
			   'content-type': 'application/json'
			  }
		payload = {'event': {'name': 'Welcome'}, 
			   'lang': lang_code, 
			   'sessionId': call_id
			  }
		response = requests.request("POST", url=apiai_url, data=json.dumps(payload), headers=headers, params=apiai_querystring)
		print response.text
		output = json.loads(response.text)
		output_text = output['result']['fulfillment']['speech']
		output_text = output_text.decode('utf-8')
		'''
		resp = VoiceResponse()
		
		# Prepare for collecting subsequent user input
		values = {'prior_text': output_text}
		qs = urllib.urlencode(values)
		action_url = '/process_speech?' + qs
		gather = Gather(input="speech", hints=hints, language=asr_lang, speechTimeout="auto", action=action_url, method="POST")
		
		# Welcome prompt played to callers during office hours
		values = {"text": output_text}
		qs = urllib.urlencode(values)
		print 'In start: before Google TTS'
		gather.play(hostname + 'goog_text2speech?' + qs)
		print 'In start: after Google TTS'
		resp.append(gather)
		
		# If user input is missing after welcome prompt (no speech input), redirect to collect speech input again
		values = {'prior_text': output_text, 
			  'asr_lang': asr_lang, 
			  'lang_code': lang_code, 
			  'SpeechResult': '', 
			  'Confidence': 0.0
			 }
		qs = urllib.urlencode(values)
		action_url = '/process_speech?' + qs
		resp.redirect(action_url)
		print str(resp)
		return str(resp)
		
#####
##### Process Twilio ASR: "Speech to Text" to Dialogflow Intent analysis
#####
@app.route('/process_speech', methods=['GET', 'POST'])
def process_speech():
	cli = request.values.get('From')
	call_id = request.values.get('CallSid')
	asr_lang = request.values.get('asr_lang', 'en-AU')
	lang_code = request.values.get('lang_code', 'en')
	prior_text = request.values.get('prior_text', 'Prior text missing')
	input_text = request.values.get('SpeechResult', '')
	confidence = float(request.values.get('Confidence', 0.0))
	hostname = request.url_root
	print "Twilio Speech to Text: " + input_text + " Confidence: " + str(confidence)
	#Check for any blanks between digits (both for employee number and mobile number)
	if re.search(r'\b\d{1,16}\b', input_text):
		input_text = re.sub('(?<=\d) (?=\d)', '', input_text)
		print "Changed input: " + input_text
	sys.stdout.flush()
	resp = VoiceResponse()
	
	if (confidence >= 0.0):
		# Step 1: Call Dialogflow for intent analysis
		intent_name, output_text, product_name, emp_id = dialogflow_text_to_intent(project_id, input_text, call_id, lang_code)
		
		# Step 2: Speech input processing by Twilio
		values = {'prior_text': output_text}
       		qs2 = urllib.urlencode(values)
        	action_url = '/process_speech?' + qs2
        	gather = Gather(input="speech", hints=hints, language=asr_lang, speechTimeout="auto", action=action_url, method="POST")
        	values = {"text": output_text}
		qs1 = urllib.urlencode(values)
		print 'In-progress: Before Google tts'
		gather.play(hostname + 'goog_text2speech?' + qs1)
		print 'In progress: After Google tts'
		resp.append(gather)
		
		# Transfer to General services if employee number is not provided
    		if intent_name == 'no_employee_number_cartwright':
			resp.dial('+61280490603')
			resp.redirect('/process_close')
			
		# Transfer for default fallback intent
		if intent_name == 'Default Fallback Intent':
			print 'reached default intent. Transfering...'
			resp.dial('+61280490603')
			resp.redirect('/process_close')
		
		# Perform employee number validation
		if intent_name == 'get_employee_number_cartwright_yes':
			#Validate employee number
			if (str(emp_id)[:2]) != '10':
				resp.dial('+61280490603')
				resp.redirect('/process_close')
		
		# Transfer to routepoint based in intent and product	
		print 'Intent :' + intent_name
		if intent_name != '' and product_name != '':
			phone_number = getroutepoint(intent_name, product_name)
			resp.dial(phone_number)
			resp.redirect('/process_close')	
			
		# If gather is missing (no speech input), redirect to process incomplete speech via Dialogflow
		values = {'prior_text': output_text, 
			  'asr_lang': asr_lang,
			  'lang_code': lang_code, 
			  'SpeechResult': '', 
			  'Confidence': 0.0}
		qs3 = urllib.urlencode(values)
		action_url = '/process_speech?' + qs3
		resp.redirect(action_url)
			
	# When confidence of speech recogniton is not enough, replay the previous conversation
	else:
		output_text = prior_text
        	values = {"prior_text": output_text}
		qs2 = urllib.urlencode(values)
		action_url = "/process_speech?" + qs2
		gather = Gather(input="speech", hints=hints, language=asr_lang, speechTimeout="auto", action=action_url, method="POST")
		values = {"text": output_text}
		qs1 = urllib.urlencode(values)
		print 'Before Google tts'
		gather.play(hostname + 'goog_text2speech?' + qs1)
		print 'After Google tts read'
		resp.append(gather)
		values = {"prior_text": output_text}
		qs2 = urllib.urlencode(values)
		action_url = "/process_speech?" + qs2
		resp.redirect(action_url)
	print str(resp)
	return str(resp)

@app.route('/process_close', methods=['GET', 'POST'])
def process_close():
	print 'in process_close'
	

	

#####
##### Google Dialogflow V2 API - Intent identification from text
#####
#@app.route('/dialogflow_text_to_intent', methods=['GET', 'POST'])
def dialogflow_text_to_intent(project_id, call_id, input_text, lang_code):

	#Generate Google Dialogflow Credentials
	service_account_info = json.loads(credentials_dgf)
	credentials = service_account.Credentials.from_service_account_info(service_account_info)

	session_client = dialogflow.SessionsClient(credentials=credentials)
	session = session_client.session_path(project_id, call_id)
	
	for text in input_text:
        	text_input = dialogflow.types.TextInput(text=text, language_code=lang_code)
		query_input = dialogflow.types.QueryInput(text=text_input)
		response = session_client.detect_intent(session=session, query_input=query_input)
		output = json.loads(response.text)
		print output
		print json.dumps(output, indent=2)
	
		# Get values from Dialogflow
		try:
			intent_name = output['query_result']['intent']['display_name']
		except:
			intent_name= ""
		try:
			product_name = output['query_result']['parameters']['optus_product']
		except:
			product_name= ""
		try:
			emp_id = output['result']['parameters']['employee_id']
		except:
			emp_id= ""	
		try:
			output_text = output['query_result']['fulfillment_text']
		except:
			output_text = ""
    	
	return intent_name, output_text, product_name, emp_id

#####
##### Get route point based on Intent and product
#####
def getroutepoint(intent_name, product_name):
	#Catch all exceptions
	phone_number = "+61280490603"
	
	# Transfer for Billing_services
    	if intent_name == 'billing_services_cartwright':
		if product_name == 'Postpaid':
			phone_number = "+61280490602"
		elif product_name == 'Prepaid':
			phone_number = "+61280490602"
		elif product_name == 'Mobile Broadband':
			phone_number = "+61280490602"
		elif product_name == 'Internet':
			phone_number = "+61280490602"
		elif product_name == 'Telephony':
			phone_number = "+61280490602"
		elif product_name == 'Optus TV':
			phone_number = "+61280490602"
		elif product_name == 'Financial Services':
			phone_number = "+61280490602"
					
	# Transfer for Sales_services
    	if intent_name == 'sales_services_cartwright':
		if product_name == 'Postpaid':
			phone_number = "+61280490601"
		elif product_name == 'Prepaid':
			phone_number = "+61280490601"
		elif product_name == 'Mobile Broadband':
			phone_number = "+61280490601"
		elif product_name == 'Internet':
			phone_number = "+61280490601"
		elif product_name == 'Telephony':
			phone_number = "+61280490601"
		elif product_name == 'Optus TV':
			phone_number = "+61280490601"
		elif product_name == 'Financial Services':
			phone_number = "+61280490601"
					
	# Transfer for Tech_services
	if intent_name == 'tech_services_cartwright':
		if product_name == 'Postpaid':
			phone_number = "+61280490600"
		elif product_name == 'Prepaid':
			phone_number = "+61280490600"
		elif product_name == 'Mobile Broadband':
			phone_number = "+61280490600"
		elif product_name == 'Internet':
			phone_number = "+61280490600"
		elif product_name == 'Telephony':
			phone_number = "+61280490600"
		elif product_name == 'Optus TV':
			phone_number = "+61280490600"
		elif product_name == 'Financial Services':
			phone_number = "+61280490600"
	
	return phone_number

#####
##### Dialogflow fulfillment webhook
#####
@app.route('/webhook', methods=['POST'])
# Receive the JSON request from Dialogflow
def webhook():
	req = request.get_json(silent=True, force=True)
	print 'Request:'
	print json.dumps(req, indent=4)
	res = processRequest(req)
	res = json.dumps(res, indent=4)
	r = make_response(res)
	r.headers['Content-Type'] = 'application/json'
	return r

# Get details from JSON 
def processRequest(req):
	result = req.get('queryResult')
	#intentname = result.intent.get('displayName')
	metadata = result.get('intent')
	intentname = metadata.get('displayName')
	parameters = result.get('parameters')
	actionname = parameters.get('action')
	emp_idn = parameters.get('employee_id')
	emp_id = str(int(emp_idn))
	print emp_id
	product_name = parameters.get('optus_product')
	
	# Process employee number
	if intentname == 'get_employee_number_cartwright':
		print 'Intent :' + intentname
		#Validate employee number
		if (emp_id[:2]) != '10':
			fulfillmentText = 'Hmmm! That does not seem to be a valid employee number. Let me transfer you to one of my colleagues in the General Customer Service Team that can help you with your inquiry today.'
		else:
			employee_name = get_employee_name(emp_id)
			fulfillmentText = 'Thanks ' + employee_name + ' for providing your employee number. Now how can we help you today?'
	
	# Get employee number again if user informs that employee id interpretation is incorrect
	elif intentname == 'get_employee_number_cartwright_no':
		fulfillmentText = 'Please provide your employee number by speaking each digit individually'
	
    	# Transfer for Billing_services
    	elif intentname == 'billing_services_cartwright':
		fulfillmentText = 'Ok. Let me transfer you to one of my colleagues that can help you with your Billing inquiry'
	
    	# Transfer for Sales_services   
    	elif intentname == 'sales_services_cartwright':
		fulfillmentText = 'Ok. Let me transfer you to one of my colleagues that can help you with your Sales inquiry'
	
    	# Transfer for Tech_services
    	elif intentname == 'tech_services_cartwright':
		fulfillmentText = 'Ok. Let me transfer you to one of my colleagues that can help you with your technical inquiry'
			
    	# Transfer to General services if employee number is not provided
    	elif intentname == 'no_employee_number_cartwright':
		fulfillmentText = 'Let me transfer you to one of my colleagues in the General Customer Service Team that can help you with your inquiry today.'
		
	# Catch all error/exception scenarios and transfer to General services
	else:
		fulfillmentText = 'Kindly hold on while we connect you to one of our customer service agent'
	
	return {'fulfillmentText': fulfillmentText, 'source': 'careforyou'}
	
	return res
	
# Helper function for getting employee name
def get_employee_name(emp_id):
	print 'Inside Get employee name'
	print emp_id
	if emp_id == '1048350':
		employee_name = 'Chris'
	elif emp_id == '1048550':
		employee_name = 'Mick'
	elif emp_id == '1048550':
		employee_name = 'Josh'
	elif emp_id == '1058670':
		employee_name = 'Paul'
	elif emp_id == '1088430':
		employee_name = 'Cameron'
	else:
		employee_name = ''
		
	return employee_name

#####
##### Google Cloud Text to speech for Speech Synthesis
##### This function calls Google TTS and then streams out the output media in mp3 format
#####
@app.route('/goog_text2speech', methods=['GET', 'POST'])
def goog_text2speech():
	text = request.args.get('text', "Hello! Invalid request. Please provide the TEXT value")
	
	# Pre-process the text 
	#if len(text) == 0:
		#text = "We are experiencing technical difficulties at the moment. Please call back later."
	
	# Adding space between numbers for better synthesis
	if re.search(r'\b\d{1,16}\b', text):
		text = re.sub('(?<=\d)(?=\d)', ' ', text)
		print "Changed input: " + text
	
	# Setting profile id
	effects_profile_id = 'telephony-class-application'
	
	#Setting credentials -  Read env data
	#credentials_raw = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
	
	#Generate Google TTS Credentials
	service_account_info = json.loads(credentials_dgf)
	credentials = service_account.Credentials.from_service_account_info(service_account_info)
		    
	# Create Google Text-To-Speech client
    	client = texttospeech.TextToSpeechClient(credentials=credentials)
	
	#Pass the text to be synthesized by Google Text-To-Speech
	input_text = texttospeech.types.SynthesisInput(text=text)
		
	#Set the Google Text-To-Speech voice parameters
    	voice = texttospeech.types.VoiceSelectionParams(language_code='en-AU', name='en-AU-Wavenet-A', ssml_gender=texttospeech.enums.SsmlVoiceGender.FEMALE)

	#Set Google Text-To-Speech audio configuration parameters
    	audio_config = texttospeech.types.AudioConfig(audio_encoding=texttospeech.enums.AudioEncoding.MP3, effects_profile_id=[effects_profile_id])

	# Request speech synthesis from Google Text-To-Speech
    	response = client.synthesize_speech(input_text, voice, audio_config)
	
	# Write the output to a temp file
	with open('output.mp3', 'wb') as out:
		out.write(response.audio_content)
		print('Audio content written to file "output.mp3"')
	
	if response.audio_content:
		# Read the audio stream from the response
		def generate():
			print 'inside google tts generate method'
			with open('output.mp3', 'rb') as dmp3:
				data = dmp3.read(1024)
				while data:
					yield data
					data = dmp3.read(1024)
			print 'generate complete for google tts'
		return Response(generate(), mimetype="audio/mpeg")
    	else:
		# The response didn't contain audio data, exit gracefully
		print("Could not stream audio")
        	return "Error"
    
if __name__ == '__main__':
	app.run(host='0.0.0.0', debug = True)