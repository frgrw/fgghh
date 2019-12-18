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


def parse_schedule(schedule: str) -> (str, dict):
    if not schedule.startswith('starting'):
        return schedule, {}

    match = re.match(r'starting\s+(?P<start>.+)\s+every\s+(?P<days>[0-9]{1,2})\s+days\s+at\s+(?P<hours>[0-9]{1,2}):(?P<minutes>[0-9]{2})', schedule)
    start = match.group('start')
    days = int(match.group('days'))
    hours = int(match.group('hours'))
    minutes = int(match.group('minutes'))

    start_date = parser.parse(start).date().isoformat()

    cron = f'{minutes} {hours} * * *'

    return cron, {'start': start_date, 'frequency': days, 'unit': 'day'}


def read_reminders(client: CloudSchedulerClient) -> typing.MutableMapping[str, Job]:
    reminder_jobs = {}
    with open('reminders.yaml', 'r') as f:
        config = yaml.safe_load(f)
        for recipient in config['recipients']:
            for reminder in recipient['reminders']:
                cron, extra_schedule = parse_schedule(reminder['schedule'])
                payload = {'from': config['from'],
                           'to': recipient['to'],
                           'subject': reminder['subject'],
                           'html_content': reminder.get('html_content')}
                if extra_schedule:
                    payload['schedule'] = extra_schedule
                data = json.dumps(payload).encode('utf-8')
                target = PubsubTarget(topic_name=f'projects/{PROJECT}/topics/{TOPIC}', data=data)
                hasher = hashlib.sha1()
                hasher.update(data)
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

