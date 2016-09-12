#!/usr/bin/python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import utils
import logger
import config
log = logger.get_logger(__name__)
conf = config.get_config()

# attach the image to the given message
def attach_image(msg,image):
        with open(image['filename'], 'r') as file:
                img = MIMEImage(file.read())
                file.close()
                img.add_header('Content-ID', '<{}>'.format(image['id']))
                msg.attach(img)

# send an email
def send(subject,body,images=[]):
	msg = MIMEMultipart()
	# attach images
	if len(images) > 0: 
		for image in images: attach_image(msg,image)
	# prepare the message
        msg['From'] = conf["notification"]["email"]["from"]
        msg['To'] = ", ".join(conf["notification"]["email"]["to"])
        msg['Subject'] = "[myHouse] "+subject
        msg.attach(MIMEText(body, 'html'))
        smtp = smtplib.SMTP(conf["notification"]["email"]["hostname"])
	# send it
	log.info("sending email '"+subject+"' to "+msg['To'])
        smtp.sendmail(conf["notification"]["email"]["from"],conf["notification"]["email"]["to"], msg.as_string())
        smtp.quit()

