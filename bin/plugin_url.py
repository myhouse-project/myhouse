#!/usr/bin/python

import sys
import os
import base64

import utils
import logger
log = logger.get_logger(__name__)

# poll the sensor
def poll(sensor):
	url = sensor["args"][0]
	# visit the url, if an image is requested, return the base64 encoded data
	if sensor["request"] == "image": content = base64.b64encode(utils.web_download(url))
	else: content = utils.web_get(url)
	return content

# parse the data
def parse(sensor,data):
	measures = []
	measure = {}
	measure["key"] = sensor["sensor_id"]
	measure["value"] = data
	measures.append(measure)
        return measures

# return the cache schema
def cache_schema(sensor):
	return sensor['sensor_id']

