import re
from dateutil import parser


def parse_schedule(schedule: str) -> (str, dict):
    if not schedule.startswith('starting'):
        return schedule, {}

    # TODO: finish this
    match = re.match(r'starting\s+(?P<start>.+)\s+every\s+(?P<days>[0-9]{1,2})\s+days\s+at\s+(?P<hours>[0-9]{1,2}):(?P<minutes>[0-9]{2})', schedule)
    start = match.group('start')
    days = int(match.group('days'))
    hours = int(match.group('hours'))
    minutes = int(match.group('minutes'))

    start_date = parser.parse(start).date().isoformat()

    cron = f'{minutes} {hours} * * *'

    return cron, {'start': start_date, 'frequency': days, 'unit': 'day'}


