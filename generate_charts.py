#!/usr/bin/python
import copy
import json
import requests
import sys

import utils
import logger
import config
log = logger.get_logger(__name__)
conf = config.get_config()

hostname = 'http://127.0.0.1:'+str(conf['web']['port'])+'/'
export_url = 'https://export.highcharts.com/'
export_data = {"width": 500, "async" : False, "type": conf['constants']['chart_extension']}

# capitalize the first letter
def capitalizeFirst(string):
	return string.capitalize()

# save the image to disk
def save_to_file(r,filename):
	with open(utils.get_widget_chart(filename),'wb') as file:
        	for chunk in r.iter_content(1000):
                	file.write(chunk)
	file.close()

# generate the chart
def generate_chart(options,filename,is_stock_chart=False):
	data = copy.deepcopy(export_data)
        data["options"] = json.dumps(options)
	if is_stock_chart: data["constr"] = "StockChart"
        r = requests.post(export_url, data=data)
	save_to_file(r,filename)

# apply the format to the value
def apply_format(series,format):
	if 'tooltip' not in series: series['tooltip'] = {} 
	if 'dataLabels' not in series: series['dataLabels'] = {}
	series['tooltip']['valueSuffix'] = conf['constants']['formats'][format]['suffix'];
	series['dataLabels']['format'] = '{y}'+conf['constants']['formats'][format]['suffix'];

# add a new point to an existing series
def add_point(chart,url,series_index):
	data = json.loads(utils.web_get(hostname+url))
	if 'data' not in chart['series'][series_index]: chart['series'][series_index]['data'] = []
	chart['series'][series_index]['data'].append(data)

# add a new series to a chart
def add_series(chart,url,sensor,series_index):
	data = json.loads(utils.web_get(hostname+url))
	# get the series template
	series = copy.deepcopy(sensor['series'][series_index])
	# set the name and the id
	series['name'] = sensor['display_name']+" "+sensor['series'][series_index]['series_id']
	series['id'] = sensor['sensor_id']+":"+sensor['series'][series_index]['series_id']
	# add the sensor suffix and tooltip
	apply_format(series,sensor['format'])
	# add the data to it
	series['data'] = data
	# if the data is a string, add flags
	if sensor['format'] == 'string':
		flags = []
		for i in range(len(data)):
			if data[i][1] == None: continue
#			flags.append({'x': int(data[i][0]), 'shape': 'url(https://icons.wxug.com/i/c/k/'+str(data[i][1])+'.gif)', 'title': '<img width="'+str(series['width'])+'" heigth="'+str(series['heigth'])+'" src="https://icons.wxug.com/i/c/k/'+str(data[i][1])+'.gif">'})
			flags.append({'x': int(data[i][0]), 'shape': 'circlepin', 'title': str(data[i][1])})
			series['data'] = flags
	# attach the series to the chart
	if 'series' not in chart: chart['series'] = []
	chart['series'].append(series)

# add a sensor summary widget
def add_group_summary_widget(widget,module_id,group):
	chart = copy.deepcopy(conf["constants"]["charts"]["chart_group_summary"])
	for i in range(len(group["sensors"])):
		sensor = group["sensors"][i];
		sensor_url = module_id+"/sensors/"+group["group_id"]+"/"+sensor["sensor_id"];
		# skip flags
		if sensor['format'] == 'string': continue
		# add the sensor to the xAxis
		chart['xAxis']['categories'].append(sensor["display_name"])
		# add the point for yesterday's range
		add_point(chart,sensor_url+"/yesterday/range",0);
		# add the point for today's range
		add_point(chart,sensor_url+"/today/range",1);
	chart['title']['text'] = widget["display_name"]
	generate_chart(chart,widget["widget_id"])

# add a sensor timeline widget
def add_group_timeline_widget(widget,module_id,group,timeframe):
	chart = copy.deepcopy(conf["constants"]["charts"]["chart_"+widget["type"]+"_"+widget["timeframe"]])
	# for each sensor
	for i in range(len(group["sensors"])):
		sensor = group["sensors"][i]
		sensor_url = module_id+"/sensors/"+group["group_id"]+"/"+sensor["sensor_id"]
		if "series" not in sensor: continue
		# add each series, to the chart
		for j in range(len(sensor["series"])):
			series = sensor["series"][j]
			add_series(chart,sensor_url+"/"+timeframe+"/"+series["series_id"],sensor,j)
	chart['title']['text'] = widget["display_name"]
        generate_chart(chart,widget["widget_id"])

# add a generic sensor chart widget
def add_chart_widget(widget,module_id,group):
	# retrieve the sensor referenced by the widget
	sensor = utils.get_sensor(module_id,group["group_id"],widget["sensor"])
	if sensor is None: return
	sensor_url = module_id+"/sensors/"+group["group_id"]+"/"+sensor["sensor_id"]
	chart = copy.deepcopy(conf["constants"]["charts"][widget["type"]])
	if sensor["format"] == "percentage": chart["yAxis"]["max"] = 100
	# add each series to the chart
	if "series" not in sensor: return
	for i in range(len(sensor["series"])):
		series = sensor["series"][i]
		add_series(chart,sensor_url+"/"+widget["timeframe"]+"/"+series["series_id"],sensor,i)
	chart['title']['text'] = widget["display_name"]
        generate_chart(chart,widget["widget_id"])

# add an image widget
def add_image_widget(widget,module_id,group):
	# retrieve the sensor referenced by the widget
	sensor = utils.get_sensor(module_id,group["group_id"],widget["sensor"])
	if sensor is None: return
	sensor_url = module_id+"/sensors/"+group["group_id"]+"/"+sensor["sensor_id"]
	r = requests.get(hostname+sensor_url+"/current")
	save_to_file(r,widget["widget_id"])

# load all the widgets of the given module
def run(requested_module,requested_widget=None):
	module_id = requested_module
	module = utils.get_module(requested_module)
	if module is None: return
	if 'widgets' not in module: return
	for i in range(len(module["widgets"])):
		for j in range(len(module["widgets"][i])):
			# for each widget
			widget = module["widgets"][i][j]
			if requested_widget is not None and widget["widget_id"] != requested_widget: continue
		        if widget["size"] == 0: continue
		        if "module" in widget: module_id = widget["module"]
		        group = utils.get_group(module_id,widget["sensor_group"])
			log.info("["+requested_module+"] generating widget "+widget["widget_id"])
		        if widget["type"] != "alerts" and group is None:
				log.warning("["+requested_module+"] invalid group "+widget["sensor_group"]+" for widget "+widget["widget_id"])
				continue
			# generate the widget
			if widget["type"] == "group_summary": add_group_summary_widget(widget,module_id,group)
			elif widget["type"] == "image": add_image_widget(widget,module_id,group)
			elif widget["type"] == "group_timeline": add_group_timeline_widget(widget,module_id,group,widget["timeframe"])
			elif widget["type"] in conf["constants"]["charts"]: add_chart_widget(widget,module_id,group)
			elif widget["type"] == "alerts": continue

# main
if __name__ == '__main__':
	if len(sys.argv) == 2: run(sys.argv[1])
	elif len(sys.argv) == 3: run(sys.argv[1],sys.argv[2])
	else: print "Usage: generate_charts.py <module_id> [widget_id]"
