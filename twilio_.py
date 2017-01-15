from twilio.rest import TwilioRestClient

cfg = {}
with open('alerts.conf') as hlr:
    for line in hlr:
        split_line = line.split('::')
        cfg[split_line[0].strip()] = split_line[1].strip()

acc = cfg['twilio_account']
token = cfg['twilio_token']
from_number = cfg['twilio_from']
to_number = cfg['twilio_to_test']

client = TwilioRestClient(acc, token)

message = client.messages.create(to=to_number, from_=from_number,
                       body="Hello --> This is me testing! :D")

sid = message.sid

body = client.messages.get(sid)
status = body.status

print status