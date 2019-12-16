import base64
import json
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def email_cloud_function(event, context):
    # Messages in pubsub are base64 encoded. Also support events with the keys directly in them, to make testing easier
    if 'data' in event:
        event = json.loads(base64.b64decode(event['data']).decode('utf-8'))
    message = Mail(
        from_email=event['from'],
        to_emails=event['to'],
        subject=event['subject'],
        html_content=event['html_content'] or ' ')  # SendGrid does not support empty body

    client = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    response = client.send(message)
    if response.status_code != 202:
        raise Exception("Sending email failed. Status code: {}".format(response.status_code))

    return "Done"
