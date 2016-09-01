from time import sleep
import datetime

import utils
import logger
import config
log = logger.get_logger(__name__)
conf = config.get_config()
import sensors
import scheduler
schedule = scheduler.get_scheduler()
import web
import db

# run the main application
def run():
	db.init()
	# schedule each sensor 
	schedule.start()
	sensors.schedule_all()
	# start the web server
	if conf['web']['enabled']: schedule.add_job(web.run,'date',run_date=datetime.datetime.now())
	while True:
		sleep(1)
 
# allow running it both as a module and when called directly
if __name__ == "__main__":
	conf["constants"]["web_use_reloader"] = False
	run()
