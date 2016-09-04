#!/usr/bin/python
import logging
import os
import time

base_dir = os.path.abspath(os.path.dirname(__file__))

# constants
constants = {
	'version': 1.1,
	'version_string': '1.1.0',
	'1_minute': 60,
	'1_hour': 3600,
	'1_day': 86400,
	'db_schema': {
		'root': "myHouse",
	},
	'null': "None",
	'base_dir': base_dir,
	'log_dir': base_dir+"/logs",
	'tmp_dir': base_dir+"/tmp",
	'email_template': base_dir+"/template_email.html",
	'service_template': base_dir+"/template_service.sh",
	'service_location': '/etc/init.d/myhouse',
	'data_expire_days': 7,
	'cache_expire_min': 1,
	'log_formatter': logging.Formatter('[%(asctime)s] [%(filename)s:%(lineno)s - %(funcName)s()] %(levelname)s: %(message)s',"%Y-%m-%d %H:%M:%S"),
	'image_unavailable': base_dir+"/web/images/image_unavailable.png",
	'web_dir': base_dir+"/web",
	'web_template': "template_web.html",
	'web_timeout': 10,
	'web_use_reloader': True,
	'formats': {
		'int': { 
			'formatter': 'int', 
			'suffix': '', 
		},
		'float': { 
			'formatter': 'float_1', 
			'suffix': '', 
		},
		'string': { 
			'formatter': 'string', 
			'suffix': '', 
		},
		'temperature': { 
			'formatter': 'float_1', 
			'suffix': u'\u00B0C', 
		},
                'humidity': {
                        'formatter': 'int',
                        'suffix': '%',
                },
		'size': { 
			'formatter': 'int', 
			'suffix': 'MB', 
		},
		'percentage': { 
			'formatter': 'float_1', 
			'suffix': '%', 
		},
		'voltage': { 
			'formatter': 'float_2', 
			'suffix': 'v', 
		},
		'length': { 
			'formatter': 'int', 
			'suffix': 'mm', 
		},
                'pressure': {
                        'formatter': 'int',
                        'suffix': 'bar',
                },
		'image': { 
			'formatter': "", 
			'suffix': "",
		},
	},
	'charts': {
		'master': {
			'chart': {
			},
			'title': {
				'text': '',
			},
			'xAxis': {
			},
			'yAxis': {
				'title': ' ',
				'opposite': True,
			},
			'credits': { 
				'enabled': False,
			},
			'legend': {
				'enabled': True,
			},
			'rangeSelector' : {
				'selected' : 0,
			},
			'tooltip': {
				'shared': True,
			},			
			'plotOptions': {
				'spline': {
					'marker': {
						'enabled': True,
					},
					'lineWidth': 3,
					'dataLabels': {
						'enabled': True,
						'y': 40,
						'borderRadius': 5,
						'backgroundColor': 'rgba(252, 255, 197, 0.7)',
						'borderWidth': 1,
						'borderColor': '#AAA',
					},
				},
				'arearange': {
					'fillOpacity': 0.2,
					'lineWidth': 1,
					'color': '#7cb5ec',
				},				
				'columnrange': {
					'grouping': False,
					'shadow': False,
					'pointWidth': 10,
					'dataLabels': {
						'enabled': True,
					},					
				},
				'bar': {
					'pointWidth': 10,
					'dataLabels': { 
						'enabled': True, 
					},
				},
				'flags': {
					'useHTML' : True,
					'color': 'gray',
					'allowPointSelect': False,
				},
			},
		},
		'chart_short': {
			'template': 'master',
			'chart': {
				'height': 194,
			},
			'xAxis': {
				'type': 'datetime',
                                'dateTimeLabelFormats': {
                                        'day': '%A',
                                },
			},
		},
		'chart_inverted': {
                        'template': 'master',
                        'chart': {
				'inverted': True,
                        },
                        'xAxis': {
                                'type': 'datetime',
                                'dateTimeLabelFormats': {
                                        'day': '%A',
                                },
                        },
                },
		'chart_short_inverted': {
			'template': 'chart_short',
			'chart': {
				'inverted': True,
				'height': 194,
			},
			'xAxis': {
				'type': 'datetime',
				'tickInterval': 24* 3600 * 1000,
				'tickWidth': 0,
				'gridLineWidth': 0,
            			'dateTimeLabelFormats': {
		        		'day': '%A',
			        },
			},
		},
		'chart_group_summary': {
			'template': 'master',
			'chart': {
				'type': 'columnrange',
				'inverted': True,
				'height': 194,
			},
			'xAxis': {
				'type': 'datetime',
				'categories': [],
			},
			'series': [
				{
					'name': 'Yesterday',
					'color': 'rgb(169,255,150)',
					'pointWidth': 18,
					'dataLabels': {
						'enabled': False,
					},
				},
				{
					'name': 'Today',
					'color': '#7cb5ec',
					'pointWidth': 10,
				},
			],
		},
		'chart_group_timeline_history': {
			'template': 'master',
			'chart': {
				'type': 'spline',
				'zoomType': 'x',
			},
			'xAxis': {
				'type': 'datetime',
				'tickInterval': 1*24*3600*1000,
				'tickWidth': 0,
				'gridLineWidth': 1,
			},
		},
		'chart_group_timeline_recent': {
			'template': 'master',
                        'chart': {
                                'type': 'spline',
                                'zoomType': 'x',
                        },
			'xAxis': {
				'type': 'datetime',
				'tickInterval': 1*3600*1000,
				'tickWidth': 0,
				'gridLineWidth': 1,
			},
			'rangeSelector': {
				'enabled': False,
			},
		},		
	},
}
# merge the chart template with the deltas
for chart_id in constants['charts']:
	chart = constants['charts'][chart_id]
	if 'template' not in chart: continue
	new_chart = constants['charts'][chart['template']].copy()
	new_chart.update(chart)
	constants['charts'][chart_id] = new_chart

# return all the configuration settings as an object
def get_constants(conf):
	# adapt the units if needed
	if conf["general"]["imperial_units"]:
		constants["formats"]["length"]["suffix"] = "in"
		constants["formats"]["length"]["formatter"] = "float_2"
        if conf["general"]["fahrenheit_temperature"]:
                constants["formats"]["temperature"]["suffix"] = u'\u00B0F'
                constants["formats"]["temperature"]["formatter"] = "int"
	return constants