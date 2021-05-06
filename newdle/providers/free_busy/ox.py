import math
from datetime import datetime

import pytz
import requests
from flask import current_app
from requests.models import HTTPBasicAuth

from ...core.util import find_overlap


MAX_WEEKS_TO_FETCH = 28


def fetch_free_busy(date, tz, uid, email):
    ox_url = current_app.config['OX_PROVIDER_URL']
    ox_username = current_app.config['OX_PROVIDER_USERNAME']
    ox_password = current_app.config['OX_PROVIDER_PASSWORD']
    ox_context_id = current_app.config['OX_PROVIDER_CONTEXT_ID']

    if not ox_url or not ox_username or not ox_password or not ox_context_id:
        raise RuntimeError('OX provider not configured!')

    user_name, server = email.split('@')

    # see how far into the future we have to fetch data
    weeks_to_fetch = math.ceil((date - datetime.now().date()).days / 7) or 1

    if weeks_to_fetch > MAX_WEEKS_TO_FETCH:
        return []

    params = {
        'contextId': ox_context_id,
        'userName': user_name,
        'server': server,
        'weeksIntoFuture': weeks_to_fetch,
    }

    resp = requests.get(
        ox_url, params=params, auth=HTTPBasicAuth(ox_username, ox_password)
    )

    if resp.status_code != 200:
        return []

    busy_slots = []

    for b_line in resp.iter_lines():
        line = b_line.decode()
        # this includes BUSY, BUSY-UNAVAILABLE and BUSY-TENTATIVE
        if line.startswith('FREEBUSY;FBTYPE=BUSY'):
            try:
                start_dt, end_dt = [
                    datetime.strptime(dt, '%Y%m%dT%H%M%S%z')
                    for dt in line.split(':')[1].split('/')
                ]

            except IndexError:
                continue

            overlap = find_overlap(date, start_dt, end_dt, pytz.timezone(tz))

            if overlap:
                busy_slots.append(overlap)

    return [
        ((start.hour, start.minute), (end.hour, end.minute))
        for start, end in busy_slots
    ]
