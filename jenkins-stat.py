#!/usr/bin/python

import json
import urllib2
import datetime
import time

url = 'https://jenkins.mosi.mirantis.net/view/All/api/json'
now = datetime.datetime.utcnow()
yesterday = now - datetime.timedelta(1)

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

        delay = 0
        for x in range(1, 5):
            delay += x
            try:
                resp = urllib2.urlopen(api_url)
                data = json.loads(resp.read())
                return data
            except Exception as e:
                print(e)
                time.sleep(delay)

        raise Exception("Failed to get data from Jenkins in 5 attempts.")

    def last_failed_build(self, url):
        return self.query(url=url, suffix='lastFailedBuild')

    def last_successful_build(self, url):
        return self.query(url=url, suffix='lastSuccessfulBuild')


jenkins = Jenkins(url='https://jenkins.mosi.mirantis.net')
all_jobs = jenkins.query()

active_jobs = []
for job in all_jobs.get('jobs', []):
    if job['color'] == 'notbuilt':
        continue
    active_jobs.append(job)

CSV_FIELDS = [
    {'name': 'Name', 'format': '{name}'},
    {'name': 'Project', 'format': '{ZUUL_PROJECT}'},
    {'name': 'Build', 'format': '{number}'},
    {'name': 'New?', 'format': '{new_issue}'},
    {'name': 'CI?', 'format': ''},
    {'name': 'Timestamp', 'format': '{timestamp}'},
    {'name': 'Duration', 'format': '{duration}'},
    {'name': 'Branch', 'format': '{ZUUL_BRANCH}'},
    {'name': 'Request', 'format': '{request}'},
    {'name': 'Logs', 'format': 'http://logs.mosi.mirantis.net/{LOG_PATH}'},
    {'name': 'Known?', 'format': ''},
    {'name': 'Issue type', 'format': ''},
    {'name': 'Reason', 'format': ''},
    {'name': 'AI', 'format': ''},
    {'name': 'FIX', 'format': ''},
]

new_data = []
for job in active_jobs:
    job_info = jenkins.query(url=job['url'])
    try:
        if job_info['healthReport'][0]['score'] == 100:
            continue
    except:
        print(job_info)
        continue

    for build in job_info['builds']:
        build_report = {
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

        build_info = jenkins.query(url=build['url'])
        if build_info['result'] == 'SUCCESS':
            continue

        for action in build_info.get('actions', [{}]):
            for parameter in action.get('parameters', [{}]):
                name = parameter.get('name', '')
                if name in ['ZUUL_PROJECT', 'ZUUL_BRANCH',
                            'ZUUL_PATCHSET', 'ZUUL_CHANGE', 'LOG_PATH']:
                    build_report[name] = parameter.get('value', '')

        build_report['name'] = job['name']
        build_report['number'] = build_info['number']
        build_report['result'] = build_info['result']
        timestamp = datetime.datetime.utcfromtimestamp(float(build_info['timestamp'])/1000)
        delta = now - timestamp
        build_report['timestamp'] = str(timestamp)
        build_report['duration'] = str(datetime.timedelta(seconds=float(build_info['duration'])/1000))
        build_report['new_issue'] = str(timestamp.date() == yesterday.date())
        if build_report['ZUUL_CHANGE']:
            build_report['request'] = 'https://review.fuel-infra.org/#/c/{ZUUL_CHANGE}/{ZUUL_PATCHSET}'.format(**build_report)
        new_data.append(build_report)


report_name = str(datetime.date.today())
with open('{}.json'.format(report_name), 'w') as f:
    json.dump(new_data, f, sort_keys=True, indent=4)


with open('{}.csv'.format(report_name), 'w') as f:
    f.write(';'.join([x['name'] for x in CSV_FIELDS]) + '\n')

    for record in new_data:
        line = (';'.join([x['format'] for x in CSV_FIELDS])).format(**record) + '\n'

        f.write(line)
