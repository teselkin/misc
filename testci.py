#!/usr/bin/python

from sh import git
from sh import ssh
from sh import scp

import json
import re
import os
import argparse
import logging

console = logging.StreamHandler()
log = logging.getLogger()
log.addHandler(console)
log.setLevel(logging.DEBUG)


class GerritClient(object):
    def __init__(self, gerrit_user, gerrit_host, gerrit_port=29418):
        self.gerrit_user = gerrit_user
        self.gerrit_host = gerrit_host
        self.gerrit_port = gerrit_port

    def _cmd(self, *args):
        cmd = []
        cmd.extend(['-p', self.gerrit_port,
                    "{0}@{1}".format(self.gerrit_user, self.gerrit_host),
                    'gerrit'])
        cmd.extend(args)
        log.debug(cmd)
        return ssh(*cmd)

    def list_projects(self, pattern='.*'):
        r = re.compile(pattern)
        for project in self._cmd('ls-projects'):
            project = project.strip()
            if r.match(project):
                yield project

    def query(self, query):
        args = [
            'query',
            '--format', 'JSON',
            query
        ]
        for s in self._cmd(*args):
            j = json.loads(s)
            if j.get('type', '') != 'stat':
                yield j

    def details(self, number):
        args = [
            'query',
            '--format', 'JSON',
            '--patch-sets',
            'change:{0}'.format(number)
        ]
        for s in self._cmd(*args):
            j = json.loads(s)
            if j.get('type', '') != 'stat':
                return j

    def review(self, change, patchset, message=None):
        args = []
        if message:
            args.extend(['--message', message])
        args.append('{0},{1}'.format(change, patchset))
        self._cmd('review', *args)


class GerritRepo(object):
    def __init__(self, project, cache_dir='/tmp', branch='master',
                 gerrit_user=None, gerrit_host=None, gerrit_port=29418):
        self.project = project
        self.cache_dir = cache_dir
        self.branch = branch
        self.repo_path = os.path.join(cache_dir, project)
        self.gerrit_user = gerrit_user
        self.gerrit_host = gerrit_host
        self.gerrit_port = gerrit_port
        self.url='ssh://{0}@{1}:{2}/{3}'.format(
            gerrit_user,
            gerrit_host,
            gerrit_port,
            project
        )

    def clone(self, force=False, commit_hook=True):
        if os.path.exists(self.repo_path):
            print('Path {0} already exists'.format(self.repo_path))
            if force:
                pass
            else:
                return

        args = [
            'clone',
            self.url,
            self.repo_path
        ]
        print('Cloning repository {0} to {1}'.format(self.project, self.repo_path))
        git(*args)

        if commit_hook:
            curr_dir = os.getcwd()
            try:
                os.chdir(self.repo_path)
                git_dir = str(git('rev-parse', '--git-dir')).strip()
                scp(
                    '-p',
                    '-P', self.gerrit_port,
                    '{0}@{1}:hooks/commit-msg'.format(self.gerrit_user, self.gerrit_host),
                    os.path.join(git_dir, 'hooks'),
                )
            finally:
                os.chdir(curr_dir)

    def checkout(self):
        pass

    def sync(self):
        curr_dir = os.getcwd()
        try:
            os.chdir(self.repo_path)
            git('clean', '-f', '-d', '-x')
            git('reset', '--hard')
            git('checkout', 'origin/{0}'.format(self.branch))
            head_commits = str(git('rev-list', 'HEAD', '--count')).strip()
            origin_commits = str(git('rev-list', 'origin/{0}'.format(self.branch), '--count')).strip()
            x = int(head_commits) - int(origin_commits)
            git('reset', '--hard', 'HEAD~{0}'.format(x))
            git('pull', '--rebase', 'origin', self.branch)
        finally:
            os.chdir(curr_dir)

    def testci(self):
        curr_dir = os.getcwd()
        try:
            os.chdir(self.repo_path)
            open('.testci', 'a').close()
            git('add', '-f', '.testci')
            git('commit', '-m', 'CI Test Commit')
            git('push', 'origin', 'HEAD:refs/for/{0}'.format(self.branch))
        finally:
            os.chdir(curr_dir)


parser = argparse.ArgumentParser()

#parser.add_argument('action')
parser.add_argument('--project', nargs='+')
parser.add_argument('--pattern', default='.*')
parser.add_argument('--branch', default='master')
parser.add_argument('--gerrit-user')
parser.add_argument('--gerrit-host')
parser.add_argument('--gerrit-port', default=29418)

args = parser.parse_args()

c = GerritClient(gerrit_user=args.gerrit_user,
                 gerrit_host=args.gerrit_host,
                 gerrit_port=args.gerrit_port)

if args.project:
    projects = args.project
else:
    projects = list(c.list_projects(pattern=args.pattern))

for project in projects:
    log.info('Processing project {0}'.format(project))
    # Recheck existing test commits
    recheck = False
    for change in c.query("project:{0} branch:{1} message:CI+Test+Commit".format(project, args.branch)):
        if 'number' in change:
            number = change.get('number')
            details = c.details(number)
            if details:
                status = details.get('status', None)
                log.debug('status = {0}'.format(status))
                if status == 'NEW':
                    patch_sets = details.get('patchSets', None)
                    if patch_sets:
                        log.info("Adding recheck message ...")
                        patchset = patch_sets[-1].get('number')
                        c.review(number, patchset, message='recheck')
                        recheck = True

    if not recheck:
        log.info("Pushing test commit ...")
        repo = GerritRepo(project=project, branch=args.branch)
        repo.clone()
        repo.sync()
        repo.testci()
