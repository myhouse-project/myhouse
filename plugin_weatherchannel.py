#!/usr/bin/python

import sys
import os
import requests
import json

import utils
import logger
import config
log = logger.get_logger(__name__)
conf = config.get_config()

# variables
url = 'https://api.weather.com/v1/geocode/'
plugin_conf = conf['plugins']['weatherchannel']

# poll the sensor
def poll(sensor):
	request = sensor['plugin']['measure']
	location = str(conf["general"]["latitude"])+","+str(conf["general"]["longitude"])
	if "location" in sensor["plugin"]: location = sensor["plugin"]["location"]
	location = location.replace(',','/')
	if request == "alerts":
		# request the web page
		return utils.web_get(url+location+'/'+get_request_type(sensor['plugin']['measure'])+'/wwir.json?apiKey='+plugin_conf['api_key']+'&units=m&language='+plugin_conf["language"])

# parse the data
def parse(sensor,data):
	request = sensor['plugin']['measure']
	# parse the json 
	parsed_json = json.loads(data)
	if request == "alerts": 
		# return the alert
		alert = ""
		if isinstance(parsed_json["forecast"]["precip_time_24hr"],basestring): alert = parsed_json["forecast"]["phrase"]
		return alert
	else: raise Exception("invalid request "+str(request))

# return the plugin request type
def get_request_type(request):
	if request == "alerts": return "forecast"

# return the cache schema
def cache_schema(sensor):
	location = str(conf["general"]["latitude"])+","+str(conf["general"]["longitude"])
	if "location" in sensor["plugin"]: location = sensor["plugin"]["location"]
	location = location.replace(',','/')
	return location+"_"+get_request_type(sensor['plugin']['measure'])
