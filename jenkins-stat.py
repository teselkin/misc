#!/usr/bin/python

import json
import urllib2
import datetime

url='https://jenkins.mosi.mirantis.net/view/All/api/json'


class Jenkins():
    def __init__(self, url):
        self.baseurl = url

    def query(self, url=None, suffix=''):
        if url:
            api_url = url
        else:
            api_url = self.baseurl
        if suffix:
            api_url += '/' + suffix
        api_url += '/api/json'

        try:
            resp = urllib2.urlopen(api_url)
            data = json.loads(resp.read())
            return data
        except Exception as e:
            print(e)
            raise e

    def last_failed_build(self, url):
        return self.query(url=url, suffix='lastFailedBuild')

    def last_successful_build(self, url):
        return self.query(url=url, suffix='lastSuccessfulBuild')


colors = {}
jenkins = Jenkins(url='https://jenkins.mosi.mirantis.net')
all_jobs = jenkins.query()

for job in all_jobs.get('jobs', []):
    if job['color'] in colors:
        colors[job['color']].append(job)
    else:
        colors[job['color']] = [job]

CSV_FIELDS = [
    {'name': 'Name', 'format': '{name}'},
    {'name': 'Project', 'format': '{ZUUL_PROJECT}'},
    {'name': 'Build number', 'format': '{number}'},
    {'name': 'New issue', 'format': '{new_issue}'},
    {'name': 'CI issue', 'format': ''},
    {'name': 'Timestamp', 'format': '{timestamp}'},
    {'name': 'Duration', 'format': '{duration}'},
    {'name': 'Branch', 'format': '{ZUUL_BRANCH}'},
    {'name': 'Request', 'format': '{request}'},
    {'name': 'Logs', 'format': 'http://logs.mosi.mirantis.net/{LOG_PATH}'},
    {'name': 'Issue type', 'format': ''},
    {'name': 'Reason', 'format': ''},
]

new_data = []
for job in colors['red']:
    build_info = {
        'name': '',
        'number': '',
        'timestamp': '',
        'duration': '',
        'result': '',
        'new_issue': '',
        'request': '',
        'ZUUL_PROJECT': '',
        'ZUUL_BRANCH': '',
        'ZUUL_CHANGE': '',
        'ZUUL_PATCHSET': '',
        'LOG_PATH': '',
    }
    job_info = jenkins.last_failed_build(url=job['url'])
    for action in job_info.get('actions', [{}]):
        for parameter in action.get('parameters', [{}]):
            name = parameter.get('name', '')
            if name in ['ZUUL_PROJECT', 'ZUUL_BRANCH',
                        'ZUUL_PATCHSET', 'ZUUL_CHANGE', 'LOG_PATH']:
                build_info[name] = parameter.get('value', '')

    build_info['name'] = job['name']
    build_info['number'] = job_info['number']
    build_info['result'] = job_info['result']
    timestamp = datetime.datetime.utcfromtimestamp(float(job_info['timestamp'])/1000)
    delta = datetime.datetime.utcnow() - timestamp
    build_info['timestamp'] = str(timestamp)
    build_info['duration'] = str(datetime.timedelta(seconds=float(job_info['duration'])/1000))
    build_info['new_issue'] = str(delta.days == 0)
    if build_info['ZUUL_CHANGE']:
        build_info['request'] = 'https://review.fuel-infra.org/#/c/{ZUUL_CHANGE}/{ZUUL_PATCHSET}'.format(**build_info)
    new_data.append(build_info)


report_name = str(datetime.date.today())
with open('{}.json'.format(report_name), 'w') as f:
    json.dump(new_data, f, sort_keys=True, indent=4)


with open('{}.csv'.format(report_name), 'w') as f:
    f.write(';'.join([x['name'] for x in CSV_FIELDS]) + '\n')

    for record in new_data:
        line = (';'.join([x['format'] for x in CSV_FIELDS])).format(**record) + '\n'

        f.write(line)
