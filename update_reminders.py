import re

import yaml
import json
import hashlib
from google.cloud.scheduler_v1 import CloudSchedulerClient
from google.cloud.scheduler_v1.types import Job, PubsubTarget

from util import parse_schedule

PROJECT = open('.gcp_project_id').read().strip()
REGION = open('.gcp_location').read().strip()
TOPIC = 'reminders-topic'
CLIENT = CloudSchedulerClient()
PARENT = CLIENT.location_path(PROJECT, REGION)


def safe_job_name(to: str, subject: str, hash: str) -> str:
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

    return CLIENT.job_path(PROJECT, REGION, job_name)


deleted = 0
for reminder in CLIENT.list_jobs(PARENT):
    CLIENT.delete_job(reminder.name)
    deleted += 1
print("Deleted {} reminders".format(deleted))

created = 0
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
            job = Job(
                name=safe_job_name(recipient['to'], reminder['subject'], hash),
                pubsub_target=target,
                schedule=cron,
                time_zone=config['timezone'])

            try:
                CLIENT.create_job(PARENT, job)
            except Exception as e:
                print(data)
                print(e)
            created += 1
print(f"Created {created} reminders")
