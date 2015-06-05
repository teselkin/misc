#!/usr/bin/env python

import os
import paramiko
import json
from datetime import date, timedelta, datetime
import re


projects_re = [
    r'^openstack/.*$',
    r'^mos-infra/.*'
]
ci_usernames = [
    'mos-infra-ci'
]

CSV_FIELDS = [
    {'name': 'Project', 'format': '{project}'},
    {'name': 'Build', 'format': '{number}'},
    {'name': 'URL', 'format': '{url}'},
    {'name': 'CI merge', 'format': '{ci_merge}'},
    {'name': 'Who merged', 'format': '{name}'},
    {'name': 'Timestamp', 'format': '{timestamp}'},
]


class Gerrit():
    def __init__(self, hostname, port=29418, username=None, key_filename=None):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.key_filename = key_filename
        self._client = None
        self._connect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _connect(self):
        ssh_config = paramiko.SSHConfig()
        user_config_file = os.path.expanduser('~/.ssh/config')
        if os.path.exists(user_config_file):
            with open(user_config_file) as f:
                ssh_config.parse(f)

        cfg = {
            'hostname': self.hostname,
            'port': self.port,
            'key_filename': None,
            'username': None,
        }

        user_config = ssh_config.lookup(cfg['hostname'])
        config_map = {
            'key_filename': 'identityfile',
            'username': 'user',
            'port': 'port',
        }
        for k1, k2 in config_map.items():
            if not cfg[k1]:
                cfg[k1] = user_config.get(k2, None)

        self._client = paramiko.SSHClient()
        # Ignore if host key is unknown
        self._client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())

        # Connect to destination host
        self._client.connect(**cfg)

    def close(self):
        self._client.close()

    def query(self, options='', query=''):
        stdin, stdout, stderr = self._client.exec_command(
            'gerrit query --format=JSON {} {}'.format(
                options, query)
        )

        for string in stdout:
            data = json.loads(string)
            if 'project' in data:
                yield data


now = date.today()
str_after = (now - timedelta(days=7)).strftime('%Y-%m-%d')
str_before = now.strftime('%Y-%m-%d')
query = 'status:merged after:{} before:{}'.format(str_after, str_before)

manual_merges = {}
with Gerrit(hostname='review.fuel-infra.org') as gerrit:
    for change in gerrit.query(options='--all-approvals', query=query):
        url = change.get('url', None)
        project = change.get('project', None)
        number = change.get('number', None)

        submit = None
        for patchset in change.get('patchSets', []):
            for approval in patchset.get('approvals', []):
                if approval['type'] == 'SUBM':
                    submit = approval

        if submit:
            if project not in manual_merges:
                manual_merges[project] = []

            manual_merges[project].append({
                'number': number,
                'url': url,
                'submit': submit
            })

report = []
for project, merges in manual_merges.items():
    if any(re.match(regex, project) for regex in projects_re):
        for merge in merges:
            report.append({
                'project': project,
                'number': merge['number'],
                'url': merge['url'],
                'ci_merge': str(merge['submit']['by']['username'] in ci_usernames),
                'name': merge['submit']['by']['name'],
                'timestamp': str(datetime.fromtimestamp(merge['submit']['grantedOn'])),
            })

report_name = str(now)
with open('merges-{}.csv'.format(report_name), 'w') as f:
    f.write(';'.join([x['name'] for x in CSV_FIELDS]) + '\n')

    for record in report:
        line = (';'.join([x['format'] for x in CSV_FIELDS])).format(**record) + '\n'
        f.write(line)
