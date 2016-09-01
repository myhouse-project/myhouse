#!/usr/bin/python
import sys
import os
import requests
import time
import math
import traceback
import datetime
import numpy
import random
import __builtin__

import logger
import config
log = logger.get_logger(__name__)
conf = config.get_config()

# remove all occurences of value from array
def remove_all(array,value):
        return [x for x in array if x != value]

# return the timestamp with a the timezone offset applied
def timezone(timestamp):
	return int(timestamp+conf["general"]["timezone_offset_hours"]*conf["constants"]["1_hour"])

# return an UTC timestamp from a local timezone timestamp
def utc(timestamp):
	return int(timestamp-conf["general"]["timezone_offset_hours"]*conf["constants"]["1_hour"])

# return the now timestamp (in the local timezone)
def now():
	return timezone(int(time.time()))

# return yesterday's timestamp (in the local timezone)
def yesterday():
	return now()-24*conf["constants"]["1_hour"]

# return the last hour timestamp
def last_hour():
	return now()-60*conf["constants"]["1_minute"]

# generate a given timestamp based on the input (in the local timezone)
def get_timestamp(years,months,days,hours,minutes,seconds):
	timestamp = datetime.datetime(years,months,days,hours,minutes,seconds,0)
	return timezone(int(time.mktime(timestamp.timetuple())))

# return day start timestamp
def day_start(timestamp):
	date = datetime.datetime.fromtimestamp(utc(timestamp))
	return get_timestamp(date.year,date.month,date.day,0,0,0)

# return day end timestamp
def day_end(timestamp):
        date = datetime.datetime.fromtimestamp(utc(timestamp))
        return get_timestamp(date.year,date.month,date.day,23,59,59)

# return hour start timestamp
def hour_start(timestamp):
        date = datetime.datetime.fromtimestamp(utc(timestamp))
        return get_timestamp(date.year,date.month,date.day,date.hour,0,0)

# return hour end timestamp
def hour_end(timestamp):
        date = datetime.datetime.fromtimestamp(utc(timestamp))
        return get_timestamp(date.year,date.month,date.day,date.hour,59,59)

# return the recent timestamp
def recent():
	return now()-conf["web"]["recent_timeframe_hours"]*conf["constants"]["1_hour"]

# return the history timestamp
def history():
	return now()-conf["web"]["history_timeframe_days"]*conf["constants"]["1_day"]

# return true if the input is a number
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

# normalize the value. If the input is a number, keep a single digit, otherwise return a string
def normalize(value):
	return float("{0:.1f}".format(float(value))) if is_number(value) else str(value)

# request a given url
def web_get(url,username=None,password=None,binary=False):
	log.debug("Requesting web page "+url)
	if username is not None: request = requests.get(url,auth=(username,password),timeout=conf['constants']['web_timeout'])
	else: request = requests.get(url,timeout=conf['constants']['web_timeout'])
	if binary: return request.content
	else: return request.text

# calculate the min of a given array of data
def min(data):
	data = remove_all(data,None)
	if len(data) > 0: 
		if is_number(data[0]): return __builtin__.min(data)
		else: return None
	else: return None

# calculate the max of a given array of data
def max(data):
	data = remove_all(data,None)
	if len(data) > 0: 
		if is_number(data[0]): return __builtin__.max(data)
		else: return None
	else: return None

# calculate the avg of a given array of data
def avg(data):
	data = remove_all(data,None)
	if len(data) > 0:
		if is_number(data[0]): return normalize(numpy.mean(data))
		else: return __builtin__.max(set(data), key=data.count)
	else: return None

# return the exception as a string
def get_exception(e):
	return traceback.format_exc(e)

# return a random int between min and max
def randint(min,max):
	return random.randint(min,max)

# return a timestamp as a human readable format
def timestamp2date(timestamp):
	return datetime.datetime.fromtimestamp(utc(int(timestamp))).strftime('%Y-%m-%d %H:%M:%S')


# truncate a long string 
def truncate(string):
	max_len = 50
	return (string[:max_len] + '...') if len(string) > max_len else string

# return the difference between two timestamps in a human readable format
def timestamp_difference(date1,date2):
	seconds = math.floor(math.fabs(date1-date2))
	interval = math.floor(seconds / 31536000)
	if interval > 1: return str(int(interval)) + " years ago"
	interval = math.floor(seconds / 2592000)
	if interval > 1: return str(int(interval)) + " months ago"
	interval = math.floor(seconds / 86400)
	if interval > 1: return str(int(interval)) + " days ago"
	interval = math.floor(seconds / 3600)
	if interval > 1: return str(int(interval)) + " hours ago"
	interval = math.floor(seconds / 60)
	if interval > 1: return str(int(interval)) + " minutes ago"
	return str(int(math.floor(seconds))) + " seconds ago"

# return a dict merging delta into template
def merge(template,delta):
	new_dict = template.copy()
	new_dict.update(delta)

# return the configuration of a given sensor	
def get_sensor2(module_id,group_id,sensor_id):
        sensor = None
        for this_module in conf['modules']:
                if this_module['module_id'] != module_id: continue
                for this_group in this_module['sensor_groups']:
                        if this_group['group_id'] != group_id: continue
                        for this_sensor in this_group['sensors']:
                                if this_sensor['sensor_id'] != sensor_id: continue
                                else:
                                        sensor = this_sensor
                                        sensor['module_id'] = this_module['module_id']
                                        sensor['group_id'] = this_group['group_id']
                                        break
	return sensor


def get_module(module_id):
	for i in range(len(conf["modules"])):
		module = conf["modules"][i]
		if module["module_id"] == module_id: return module

def get_group(module_id,group_id):
	module = get_module(module_id)
	for i in range(len(module["sensor_groups"])):
		group = module["sensor_groups"][i]
		if group["group_id"] == group_id: return group
	
def get_sensor(module_id,group_id,sensor_id):
	group = get_group(module_id,group_id)
	for j in range (len(group["sensors"])):
		sensor = group["sensors"][j]
		if sensor["sensor_id"] == sensor_id: return sensor
	
	
