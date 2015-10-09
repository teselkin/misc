#!/usr/bin/python

import json
import urllib2
import time


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

    def to_csv(self, suffix='', key='jobs'):
        for item in self.query(suffix=suffix)[key]:
            print(item)


jenkins = Jenkins(url='http://jenkins.mosi.mirantis.net')
jenkins.to_csv(suffix='view/Experimental')

