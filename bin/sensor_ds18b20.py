#!/usr/bin/python
##
# Sensor for DS18B20
# args: [<latitude>,<longitude>]
# measures: temperature

import sys
import os

import utils
import logger
log = logger.get_logger(__name__)

# poll the sensor
def poll(sensor):
	if sensor["type"] == "temperature":
		sensor_id = sensor["args"][0]
		log.debug("Reading "+'/sys/bus/w1/devices/'+sensor_id+'/w1_slave')
		# read and return the value from the sensor
	        with open('/sys/bus/w1/devices/'+sensor_id+'/w1_slave', 'r') as content_file:
			return content_file.read()

# parse the data
def parse(sensor,data):
	measures = []
	measure = {}
	measure["type"] = sensor["type"]
	if sensor["type"] == "temperature":
		# retrieve and convert the temperature
		start = data.find("t=")
	        measure["value"] = float(data[start+2:start+7])/1000
	# append the measure and return it
	measures.append(measure)
        return measures

# return the cache schema
def cache_schema(type):
	return type

