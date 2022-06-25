import base64
import datetime
import json
import os
from dateutil import parser
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


RETRY_TIMEOUT = 24*60*60


def check_ndays_schedule(start_date: datetime.date, event_date: datetime.date, frequency_days: int) -> bool:
    if event_date < start_date:
        return False

    if (event_date - start_date).days % frequency_days != 0:
        return False

    return True


def check_day_of_week(event_date: datetime.date, day_of_week: int) -> bool:
    return event_date.isoweekday() == day_of_week


def email_cloud_function(event, context):
    # Messages in pubsub are base64 encoded. Also support events with the keys directly in them, to make testing easier
    if 'data' in event:
        event = json.loads(base64.b64decode(event['data']).decode('utf-8'))

    if 'required_day_of_week' in event:
        event_date = parser.parse(context.timestamp).date()
        if not check_day_of_week(event_date, event['required_day_of_week']):
            return "Skipped"

    if 'schedule' in event:
        schedule = event['schedule']
        assert schedule['unit'] == 'day'
        start_date = datetime.date.fromisoformat(schedule['start'])
        event_date = parser.parse(context.timestamp).date()
        if not check_ndays_schedule(start_date, event_date, schedule['frequency']):
            return "Skipped"

    event_timestamp = parser.parse(context.timestamp)
    event_age = (datetime.datetime.now(datetime.timezone.utc) - event_timestamp).total_seconds()
    if event_age > RETRY_TIMEOUT:
        print('Dropped event {} ({}sec old)'.format(context.event_id, event_age))
        return 'Timeout'

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
