from read_cfg import read_cfg
from twilio.rest import TwilioRestClient

conf = read_cfg()
acc = conf['twilio_account']
token = conf['twilio_token']
from_number = conf['twilio_from']
to_number = conf['twilio_to']

client = TwilioRestClient(acc, token)

message = client.messages.create(to=to_number, from_=from_number,
                       body="Hello from Python!")

sid = message.sid

body = client.messages.get(sid)
status = body.status

print status