## Installation:
* install python 2.7.12
* add C:\Python27 and C:\Python27\Scripts to the system Path env variable
* pip install -U selenium
* pip install twilio

## Files:
__users.csv__  
* In this file we keep users email addresses.
In the future, we'll use it to turn off, on alerts for a particular user.

__alerts.csv__
* We save all alerts that have been sent out in this file in order to keep
track of them.

__creds.cfg.template__
* this is a template for alerts.conf, so rename the file and fill in the required settings.

__twilio_.py__
* The file is used only for testing purposes to test twilio.

## Run:
python run_alert.py

in verbose mode:
python run_alert.py --verbose

When the script starts, it launches the Chrome browser and fetches all user data
and sends emails, text messages accordingly.
Phone numbers are retrieved from the web app, however email addresses must be
provided in the users.csv file


## Links:

https://www.fullstackpython.com/blog/send-sms-text-messages-python.html
