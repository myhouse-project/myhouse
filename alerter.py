#!/usr/bin/python
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import time
import json
import datetime
import re
import copy

import utils
import db
import logger
import config
log = logger.get_logger(__name__)
conf = config.get_config()
import scheduler
schedule = scheduler.get_scheduler()
import output
import sensors
import image_utils

# for an image apply the configured object detection techniques
def analyze_image(sensor,data):
	alert_text = ""
	if len(data) == 0: return [alert_text]
	# detect movements if there are at least two images
	if "motion_detection" in sensor and len(data) >= 2:
		result = image_utils.detect_movement(sensor,data,is_base64=True)
		if result is not None:
			difference = result[0]
			image = result[1]
			if difference > 0: log.info("["+sensor["module_id"]+"]["+sensor["group_id"]+"]["+sensor["sensor_id"]+"] motion detected: "+str(difference)+"%")
			if difference > sensor["motion_detection"]["threshold"]:
				# save the image on disk
				image_utils.save_tmp_image("motion_detection",image)
				alert_text = utils.lang(sensor["motion_detection"]["display_name"])+" ("+str(difference)+"%)"
        # detect objects in the last image
        if "object_detection" in sensor:
                result = image_utils.detect_objects(sensor,data[(len(data)-1)],is_base64=True)
                if result is not None:
                        # detect something
                        text = result[0]
                        image = result[1]
                        # save the image on disk
                        image_utils.save_tmp_image("objects_detection",image)
                        # save a new image with the object highlighted into the sensor
                        measures = []
                        measure = {}
                        measure["key"] = sensor["sensor_id"]
                        measure["value"] = image
                        measures.append(measure)
                        sensors.store(sensor,measures)
                        # return the alert text
			log.info("["+sensor["module_id"]+"]["+sensor["group_id"]+"]["+sensor["sensor_id"]+"] object detected: "+text)
                        alert_text = text
	return [alert_text]

# retrieve for the database the requested data
def get_data(sensor,request):
	split = request.split(',')
	key = split[0]
	start = split[1]
	end = split[2]
	transform = split[3] if len(split) > 3 else None
	key_split = key.split(":")
	# adjust start and end based on the request
	query = None
	if utils.is_number(start) and utils.is_number(end):
		# request range with start and end the relative positions
		query = db.range
	else:
		# request a timerange with start and end relative times from now
		query = db.rangebyscore
		start = utils.string2timestamp(start)
		end = utils.string2timestamp(end)
	# remove the module from the key
	key = key.replace(key_split[0]+":","",1)	
	key = conf["constants"]["db_schema"]["root"]+":"+key_split[0]+":"+key
	# handle special requests
	if transform is not None and transform == "elapsed":
		# retrieve the timestamp and calculate the time difference
		data = query(key,start=start,end=end,withscores=True)
		if len(data) == 0: return []
		time_diff = (utils.now() - data[0][0])/60
		return [time_diff]
	elif transform is not None and transform == "timestamp":
		# retrieve the timestamp 
		data = query(key,start=start,end=end,withscores=True)
		if len(data) == 0: return []
		return [data[0][0]]
	elif transform is not None and transform == "distance":
		# calculate the distance between the point and our location
		data = query(key,start=start,end=end,withscores=False,formatter=conf["constants"]["formats"][sensor["format"]]["formatter"])
		if len(data) == 0: return []
		data = json.loads(data[0])
		distance = utils.distance([data["latitude"],data["longitude"]],[conf["general"]["latitude"],conf["general"]["longitude"]])
		return [int(distance)]
        elif transform is not None and transform == "count":
                # count the number of items selected
                data = query(key,start=start,end=end,withscores=False)
                return [len(data)]
	else: 
		# just retrieve the data
		data = query(key,start=start,end=end,withscores=False,formatter=conf["constants"]["formats"][sensor["format"]]["formatter"])
		if sensor["format"] == "calendar": data = utils.parse_calendar(data)
		if sensor["format"] == "position": 
			# define the key to return
			key = "label"
			if transform is not None and transform == "text": key = "text"
			data = utils.parse_position(data,key)
		if sensor["format"] == "image": data = analyze_image(sensor,data)
	return data

# evaluate if a condition is met
def is_true(a,operator,b):
	evaluation = True
	# get a's value
	if not isinstance(a,list): a = [a]
	a = a[0]
	# prepare b's value
	if not isinstance(b,list): b = [b]
	# b can be have multiple values, cycle through all of them
	for value in b:
		if value is None or a is None: evaluation = False
		elif operator == "==":
			if value != a: evaluation = False
		elif operator == "!=":
			if value == a: evaluation = False
		elif operator == ">":
			if not utils.is_number(value) or not utils.is_number(a): return False
			if float(value) >= float(a): evaluation = False
		elif operator == "<":
			if not utils.is_number(value) or not utils.is_number(a): return False
			if float(value) <= float(a): evaluation = False
		else: evaluation = False
	# return the evaluation
	return evaluation

# calculate a sub expression
def sub_expression(a,operator,b):
        # prepare the values (can be an array)
        if isinstance(a,list): a = a[0]
	if isinstance(b,list): b = b[0]
	# perform integrity checks
	if a is None or b is None: return None
	if not utils.is_number(a) or not utils.is_number(b): return None
	# calculate the expression
	if operator == "+": return float(a)+float(b)
	elif operator == "-": return float(a)-float(b)
	elif operator == "*": return float(a)*float(b)
	elif operator == "/": return float(a)/float(b)
	return None

# evaluate if the given alert has to trigger
def run(module_id,rule_id,notify=True):
	alert_text = ""
	try: 
		module = utils.get_module(module_id)
		for rule_template in module["rules"]:
			if not rule_template["enabled"]: continue
			# retrive the rule for the given rule_id
			if rule_template["rule_id"] != rule_id: continue
			# for each variable (if provided) run a different evaluation
			variables = [""]
			variable_sensor = None
			if "for" in rule_template: variables = rule_template["for"]
			for variable in variables:
				# ensure the variable is a valid sensor
				if variable != '' and utils.is_sensor(variable):
					variable_sensor = utils.get_sensor_string(variable)
					if variable_sensor is None:
						log.error("invalid variable sensor "+variable)
						continue
				# restore the template
				rule = copy.deepcopy(rule_template)
				# for each definition retrieve the data
				definitions = {}
				suffix = {}
				valid_data = True
				for definition in rule["definitions"]:
					if utils.is_sensor(rule["definitions"][definition]):
						rule["definitions"][definition] = rule["definitions"][definition].replace("%i%",variable)
						# check if the sensor exists
						split = rule["definitions"][definition].split(',')
						key = split[0]
						start = split[1]
						end = split[2]
						sensor = utils.get_sensor_string(key)
						if sensor is None:
							log.error("invalid sensor "+key)
							valid_data = False
							break
						sensors.init_plugins()
						sensor = sensors.init_sensor(sensor)
						# retrieve and store the data
						definitions[definition] = get_data(sensor,rule["definitions"][definition])
						if len(definitions[definition]) == 0: 
							log.debug("invalid data from sensor "+key)
							valid_data = False
							break
						# store the suffix
						suffix[definition] = conf["constants"]["formats"][sensor["format"]]["suffix"].encode('utf-8')
					else: 
						definitions[definition] = rule["definitions"][definition]
				# if not all the data is valid, return
				if not valid_data: continue
				# for each condition check if it is true
				evaluation = True
				for condition in rule["conditions"]:
					condition = re.sub(' +',' ',condition)
					# look for sub expressions and calculate them
					expressions = re.findall("\(([^\)]+)\)",condition)
					for i in range(len(expressions)):
						expression = expressions[i]
						placeholder = "%exp_"+str(i)+"%"
						exp1,operator,exp2 = expression.split(' ')
						# calculate the sub expression
						exp_value = sub_expression(definitions[exp1],operator,definitions[exp2])
						log.debug("["+module_id+"]["+rule_id+"] resolving "+exp1+" ("+str(definitions[exp1])+") "+operator+" "+exp2+" ("+str(definitions[exp2])+"): "+str(exp_value)+" (alias "+placeholder+")")
						# add the sub expressions to the definitions
						definitions[placeholder] = exp_value
						condition = condition.replace("("+expression+")",placeholder)
					# do the comparison and apply the condition
					a,operator,b = condition.split(' ')
					sub_evaluation = is_true(definitions[a],operator,definitions[b])
					log.debug("["+module_id+"]["+rule_id+"] evaluating "+a+" ("+str(definitions[a])+") "+operator+" "+b+" ("+str(definitions[b])+"): "+str(sub_evaluation))
					if not sub_evaluation: evaluation = False
				log.debug("["+module_id+"]["+rule_id+"] evaluates to "+str(evaluation))
				# evaluate the conditions
				if not evaluation: continue
				# alert has triggered, prepare the alert text
				alert_text = utils.lang(rule["display_name"])
				# replace the variable if needed
				if variable_sensor is not None: alert_text = alert_text.replace("%i%",utils.lang(variable_sensor["display_name"]))
				# replace the definitions placeholders
				for definition in rule["definitions"]:
					value = definitions[definition][0] if isinstance(definitions[definition],list) else definitions[definition]
					# apply aliases
					if "aliases" in rule:
						for to_find,to_replace in rule["aliases"].iteritems():
							if str(value) == str(to_find): value = to_replace
					# add the suffix
					if utils.is_sensor(rule["definitions"][definition]) and "elapsed" in rule["definitions"][definition]: 
						value = str(value)+" minutes"
					if utils.is_sensor(rule["definitions"][definition]) and "timestamp" in rule["definitions"][definition]:
						value = utils.timestamp2date(value)
					if utils.is_sensor(rule["definitions"][definition]) and "distance" in rule["definitions"][definition]:
						if conf["general"]["units"]["imperial"]: value = str(value)+" miles"
						else: value = str(value)+" km"
					elif utils.is_sensor(rule["definitions"][definition]): value = str(value)+suffix[definition]
					alert_text = alert_text.replace("%"+definition+"%",str(value))
				# execute an action
				if "actions" in rule:
					for action in rule["actions"]:
						# replace the definitions placeholders
						action = action.replace("%i%",variable)
						for definition in rule["definitions"]:
							value = definitions[definition][0] if isinstance(definitions[definition],list) else definitions[definition]
							action = action.replace("%"+definition+"%",str(value))
						# parse the action
						split = action.split(',')
						what = split[0]
						key = split[1]
						value = split[2]
						force = True if len(split) > 3 and split[3] == "force" else False
						ifnotexists = True if len(split) > 3 and split[3] == "ifnotexists" else False
						# ensure the target sensor exists
						sensor = utils.get_sensor_string(key)
						if sensor is None: 
							log.warning("["+rule["rule_id"]+"] invalid sensor "+key)
							continue
						# execute the requested action
						if what == "send": sensors.data_send(sensor["module_id"],sensor["group_id"],sensor["sensor_id"],value,force=force)
						elif what == "set": sensors.data_set(sensor["module_id"],sensor["group_id"],sensor["sensor_id"],value,ifnotexists=ifnotexists)
				# notify about the alert
				if rule["severity"] == "none": notify = False
				if notify:
					log.info("["+module_id+"]["+rule_id+"]["+rule["severity"]+"] "+alert_text)
					if rule["severity"] != "debug":
						db.set(conf["constants"]["db_schema"]["alerts"]+":"+rule["severity"],alert_text,utils.now())
						output.notify(rule["severity"],alert_text)
	except Exception,e:
		log.warning("error while running rule "+module_id+":"+rule_id+": "+utils.get_exception(e))
	return alert_text


# purge old data from the database
def expire():
	total = 0
	for stat in [':alert',':warning',':info']:
		key = conf["constants"]["db_schema"]["alerts"]+stat
		if db.exists(key):
			deleted = db.deletebyscore(key,"-inf",utils.now()-conf["alerter"]["data_expire_days"]*conf["constants"]["1_day"])
			log.debug("expiring from "+stat+" "+str(total)+" items")
			total = total + deleted
	log.info("expired "+str(total)+" items")
		
# run the given schedule
def run_schedule(run_every):
	# for each module
	log.debug("evaluate all the rules configured to run every "+run_every)
	for module in conf["modules"]:
		if not module["enabled"]: continue
		if "rules" not in module: continue
		# for each configured rule
		for rule in module["rules"]:
			if not rule["enabled"]: continue
			if rule["run_every"] != run_every: continue
			# if the rule has the given run_every, run it
			run(module["module_id"],rule["rule_id"])

# schedule both hourly and daily alerts
def schedule_all():
	log.info("starting alerter module...")
	# run now startup rules
	schedule.add_job(run_schedule,'date',run_date=datetime.datetime.now(),args=["startup"])
	# schedule minute, hourly and daily jobs
	schedule.add_job(run_schedule,'cron',second="30",args=["minute"])
	schedule.add_job(run_schedule,'cron',minute="*/5",args=["5 minutes"])
	schedule.add_job(run_schedule,'cron',minute="*/10",args=["10 minutes"])
	schedule.add_job(run_schedule,'cron',minute="*/30",args=["30 minutes"])
	schedule.add_job(run_schedule,'cron',minute="1",args=["hour"])
	schedule.add_job(run_schedule,'cron',hour="1",args=["day"])
	# schedule an expire job
	schedule.add_job(expire,'cron',hour="1")

# return the latest alerts for a web request
def data_get_alerts(severity,timeframe):
	start = utils.recent()
	if timeframe == "recent": start = utils.recent(hours=conf["general"]["timeframes"]["alerter_recent_hours"])
	if timeframe == "history": start = utils.history(days=conf["general"]["timeframes"]["alerter_history_days"])
	return json.dumps(db.rangebyscore(conf["constants"]["db_schema"]["alerts"]+":"+severity,start,utils.now(),withscores=True,format_date=True))

# allow running it both as a module and when called directly
if __name__ == '__main__':
	if len(sys.argv) != 3:
		# no arguments provided, schedule all alerts
		schedule.start()
		schedule_all()
		while True:
			time.sleep(1)
	else:
		# <module_id> <rule_id>
		run(sys.argv[1],sys.argv[2])
