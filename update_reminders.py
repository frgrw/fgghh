import os
import re
import typing

import yaml
import json
import hashlib
from dateutil import parser
from google.cloud.scheduler_v1 import CloudSchedulerClient
from google.cloud.scheduler_v1.types import Job, PubsubTarget


PROJECT = os.environ['GCP_PROJECT']
REGION = os.environ['GCP_REGION']
TOPIC = 'reminders-topic'


def safe_job_name(to: str, subject: str, hash: str, client: CloudSchedulerClient) -> str:
    base = f'projects/{PROJECT}/locations/{REGION}/jobs/'
    limit = 500 - len(base) # reserve space for base of id
    limit -= (len(hash) + 1) # reserve space for '-{hash}'

    job_name = to
    limit -= len(to)

    job_name += '-'
    limit -= 1

    job_name += subject[:limit]
    job_name += ('-' + hash)

    job_name = re.sub('[^a-zA-Z0-9]', '-', job_name)

    return client.job_path(PROJECT, REGION, job_name)


def parse_schedule(schedule: str) -> (str, dict, typing.Optional[int]):
    if schedule.startswith('starting'):
        match = re.match(r'starting\s+(?P<start>.+)\s+every\s+(?P<days>[0-9]{1,3})\s+days\s+at\s+(?P<hours>[0-9]{1,2}):(?P<minutes>[0-9]{2})', schedule)
        start = match.group('start')
        days = int(match.group('days'))
        hours = int(match.group('hours'))
        minutes = int(match.group('minutes'))

        start_date = parser.parse(start).date().isoformat()

        cron = f'{minutes} {hours} * * *'

        return cron, {'start': start_date, 'frequency': days, 'unit': 'day'}, None

    if schedule.startswith('on'):
        match = re.match(r'on\s+(?P<ordinal>[a-zA-Z1-5]+)\s+(?P<dayofweek>[a-zA-Z]{3,4})\s+in\s+(?P<month>[a-zA-Z]{3,4})\s+at\s+(?P<hours>[0-9]{1,2}):(?P<minutes>[0-9]{2})', schedule)
        ordinal = match.group('ordinal')
        day_of_week = match.group('dayofweek').lower()
        month = parser.parse(match.group('month')).month
        hours = int(match.group('hours'))
        minutes = int(match.group('minutes'))

        if ordinal == '1st':
            day_range = '1-7'
        elif ordinal == '2nd':
            day_range = '8-14'
        elif ordinal == '3rd':
            day_range = '9-21'
        elif ordinal == '4th':
            day_range = '22-28'
        else:
            raise Exception("unsupported ordinal: " + ordinal)

        cron = f'{minutes} {hours} {day_range} {month} *'

        if day_of_week.startswith('mon'):
            day_of_week = 1
        elif day_of_week.startswith('tue'):
            day_of_week = 2
        elif day_of_week.startswith('wed'):
            day_of_week = 3
        elif day_of_week.startswith('thu'):
            day_of_week = 4
        elif day_of_week.startswith('fri'):
            day_of_week = 5
        elif day_of_week.startswith('sat'):
            day_of_week = 6
        elif day_of_week.startswith('sun'):
            day_of_week = 7
        else:
            raise Exception("unsupported day of week: " + day_of_week)

        return cron, {}, day_of_week

    return schedule, {}, None


def read_reminders(client: CloudSchedulerClient) -> typing.MutableMapping[str, Job]:
    reminder_jobs = {}
    with open('reminders.yaml', 'r') as f:
        config = yaml.safe_load(f)
        for recipient in config['recipients']:
            for reminder in recipient['reminders']:
                cron, extra_schedule, day_of_week = parse_schedule(reminder['schedule'])
                payload = {'from': config['from'],
                           'to': recipient['to'],
                           'subject': reminder['subject'],
                           'html_content': reminder.get('html_content')}
                if extra_schedule:
                    payload['schedule'] = extra_schedule
                if day_of_week is not None:
                    payload['required_day_of_week'] = day_of_week
                data = json.dumps(payload).encode('utf-8')
                target = PubsubTarget(topic_name=f'projects/{PROJECT}/topics/{TOPIC}', data=data)
                hasher = hashlib.sha1()
                hasher.update(data)
                hasher.update(cron.encode('utf-8'))
                hash = hasher.hexdigest()
                job_name = safe_job_name(recipient['to'], reminder['subject'], hash, client)
                job = Job(
                    name=job_name,
                    pubsub_target=target,
                    schedule=cron,
                    time_zone=config['timezone'])
                reminder_jobs[job_name] = job

    return reminder_jobs


if __name__ == '__main__':
    client = CloudSchedulerClient()
    parent = client.location_path(PROJECT, REGION)
    reminder_jobs = read_reminders(client)

    deleted = 0
    unchanged = 0
    for reminder in client.list_jobs(parent):
        if reminder.name in reminder_jobs:
            del reminder_jobs[reminder.name]
            unchanged += 1
        else:
            client.delete_job(reminder.name)
            deleted += 1
    print("{} unchanged reminders".format(unchanged))
    print("Deleted {} reminders".format(deleted))

    created = 0
    for reminder in reminder_jobs.values():
        try:
            client.create_job(parent, reminder)
        except Exception as e:
            print(reminder)
            print(e)
        created += 1
    print(f"Created {created} reminders")

