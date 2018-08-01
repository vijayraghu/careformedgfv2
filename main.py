# -*- coding: utf-8 -*-
import os
import sys
import urllib
import requests
import json
from google.protobuf.json_format import MessageToJson
import re
import datetime
from flask import Flask, request, Response, make_response, jsonify, url_for
from contextlib import closing
# Twilio Helper Library
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Dial
# Google Text To Speech SDK
from google.oauth2 import service_account
from google.cloud import texttospeech_v1beta1 as texttospeech
# Dialogflow V2 SDK
import dialogflow


#####
##### Declare Global variables
#####
# Setting Google ID - Read env data
project_id = os.environ["DIALOGFLOW_PROJECT_ID"]
#Setting Google authorization credentials -  Read env data
credentials_dgf = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
call_id = "12345"
lang_code = 'en'

app = Flask(__name__)

# Receive call from Twilio with paramters
@app.route('/welcome', methods=['GET','POST'])
def welcome():
	#Setting Google Dialogflow Credentials and invoking SDK
	service_account_info = json.loads(credentials_dgf)
	credentials = service_account.Credentials.from_service_account_info(service_account_info)
	session_client = dialogflow.SessionsClient(credentials=credentials)
	session = session_client.session_path(project_id, call_id)
	event_input = dialogflow.types.EventInput(name='Welcome', language_code=lang_code)
	query_input = dialogflow.types.QueryInput(event=event_input)
	response = session_client.detect_intent(session=session, query_input=query_input)
	print response		
	output_text = response.query_result.fulfillment_text
	output_text = output_text.decode('utf-8')
	print output_text
	return output_text
	
#####
##### Process Twilio ASR: "Speech to Text" to Dialogflow Intent analysis
#####
@app.route('/process_speech', methods=['GET', 'POST'])
def process_speech():
	input_text = request.values.get('input_text', '')
	print input_text
	# Step 1: Call Dialogflow for intent analysis
	intent_name, output_text, optus_product, emp_id = dialogflow_text_to_intent(project_id, call_id, input_text, lang_code)
	print intent_name, output_text, optus_product, emp_id
	return intent_name, output_text, optus_product, emp_id

#####
##### Google Dialogflow V2 API - Intent identification from text
#####
#@app.route('/dialogflow_text_to_intent', methods=['GET', 'POST'])
def dialogflow_text_to_intent(project_id, call_id, input_text, lang_code):
	print project_id, call_id, input_text, lang_code
	#Setting Google Dialogflow Credentials and invoking SDK
	service_account_info = json.loads(credentials_dgf)
	credentials = service_account.Credentials.from_service_account_info(service_account_info)
	session_client = dialogflow.SessionsClient(credentials=credentials)
	session = session_client.session_path(project_id, call_id)
	if input_text:
		text_input = dialogflow.types.TextInput(text=input_text, language_code=lang_code)
		query_input = dialogflow.types.QueryInput(text=text_input)
		response = session_client.detect_intent(session=session, query_input=query_input)
		print response
		jsonObj = MessageToJson(response.query_result)
		output = json.loads(jsonObj)
		#output_parameter_product = output["parameters"]["optus_product"]
		#print output_parameter_product
		#output_parameter_empid = output["parameters"]["employee_id"]
		#print output_parameter_empid
		
		# Return properties from Dialogflow
		try:
			#intent_name = response.query_result.intent.display_name
			intent_name = output["intent"]["displayName"]
		except:
			intent_name= ""
		try:	
			#optus_product = response.query_result.parameters.fields.optus_product
			optus_product = output["parameters"]["optus_product"]
		except:
			product_name= ""
		try:
			#emp_id = response.query_result.parameters.fields.employee_id
			emp_id = output["parameters"]["employee_id"]
		except:
			emp_id= ""	
		try:
			#output_text = response.query_result.fulfillment_text
			output_text = output["fulfillmentText"]
		except:
			output_text = ""
    	
	return intent_name, output_text, optus_product, emp_id
  
if __name__ == '__main__':
	app.run(host='0.0.0.0', debug = True)
