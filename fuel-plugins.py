#!/usr/bin/python

import requests
import json
from datetime import date, datetime

TOKEN=''
SINCE_DATE='2015-01-01'

class GitHub(object):
    def __init__(self, **config_options):
        self.__dict__.update(**config_options)
        self.url = 'https://api.github.com'
        self.session = requests.Session()
        if hasattr(self, 'api_token'):
           self.session.headers['Authorization'] = 'token %s' % self.api_token
        elif hasattr(self, 'username') and hasattr(self, 'password'):
           self.session.auth = (self.username, self.password)

    def get_response(self, url, nodata=None):
        while url:
            print '# {}'.format(url)
            response = self.session.get(url)
            url = response.links.get('next', {}).get('url', None)
            try:
                yield json.loads(response.text)
            except:
                yield nodata

    def search(self, url=None, query=None):
        if url is None:
            url = '{}/search/{}'.format(self.url, query)
        items = []
        for page in self.get_response(url):
            items.extend(page['items'])
        return items

    def user_profile(self, url):
        for gh_profile in self.get_response(url):
            profile = {
                'login': gh_profile.get('login', ''),
                'html_url': gh_profile.get('html_url', ''),
                'name': gh_profile.get('name', ''),
                'email': gh_profile.get('email', ''),
                'company': gh_profile.get('company', '')
            }
        return profile
            

    def most_active_contributors(self, url, since_date=None, until_date=None,
                                 sort_by=None, sort_desc=False):
        url = '{}/stats/contributors'.format(url)
        if since_date:
            since_date = datetime.strptime(since_date, "%Y-%m-%d")
        if until_date:
            until_date = datetime.strptime(until_date, "%Y-%m-%d")
        contrib_stat = []
        for page in self.get_response(url, nodata=[]):
            for stats in page:
                user_stat = {
                    'login': stats['author']['login'],
                    'url': stats['author']['url'],
                    'additions': 0,
                    'commits': 0,
                    'deletions': 0,
                }
                for week_stat in stats['weeks']:
                    if since_date and datetime.fromtimestamp(week_stat['w']) < since_date:
                        continue
                    if until_date and datetime.fromtimestamp(week_stat['w']) > until_date:
                        continue
                    user_stat['commits'] += week_stat['c']
                    user_stat['additions'] += week_stat['a']
                    user_stat['deletions'] += week_stat['d']
                if user_stat['commits'] + user_stat['additions'] + user_stat['deletions'] > 0:
                    contrib_stat.append(user_stat)
        if sort_by:
            return sorted(contrib_stat, key=lambda k: k[sort_by], reverse=sort_desc)
        return contrib_stat

github = GitHub(api_token=TOKEN)
users = {}
for repo in github.search(query='repositories?q=fuel-plugin'):
    if repo['owner']['login'] != 'openstack':
        continue
    contributors = github.most_active_contributors(url=repo['url'],
                                                   since_date=SINCE_DATE,
                                                   sort_by='commits',
                                                   sort_desc=True)[:3]
    print u'{}; owner'.format(repo['name'])
    for contributor in contributors:
        print u'{}; contributor; {}; {}'.format(repo['name'],
                                                contributor['login'],
                                                contributor['commits'])
        if users.get(contributor['login'], None) is None:
            users[contributor['login']] = github.user_profile(contributor['url'])

for user in users.values():
    print u'{login}; {html_url}; {name}; {email}; {company}'.format(**user)

