#!/usr/bin/python

from sh import git
from sh import ssh
from sh import scp

from prettytable import PrettyTable

import json
import re
import os
import argparse
import logging
import sys


console = logging.StreamHandler()
log = logging.getLogger()
log.addHandler(console)
log.setLevel(logging.INFO)


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

    def details(self, number, comments=False):
        args = [
            'query',
            '--format', 'JSON',
            '--patch-sets',
            'change:{0}'.format(number)
        ]
        if comments:
            args.append('--comments')
        for s in self._cmd(*args):
            j = json.loads(s)
            if j.get('type', '') != 'stat':
                return j

    def review(self, revision, message=None, abandon=False):
        args = []
        if abandon:
            args.append('--abandon')
        if message:
            args.extend(['--message', message])
        args.append(revision)
        self._cmd('review', *args)


class GerritRepo(object):
    def __init__(self, project, branch='master', cache_dir=None,
                 gerrit_user=None, gerrit_host=None, gerrit_port=29418,
                 message=None):
        self.project = project
        self.branch = branch
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            self.cache_dir = os.path.join(os.getenv('HOME'),
                                          '.cache/git', gerrit_host)
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.repo_path = os.path.join(self.cache_dir, self.project)
        self.gerrit_user = gerrit_user
        self.gerrit_host = gerrit_host
        self.gerrit_port = gerrit_port
        self.url='ssh://{0}@{1}:{2}/{3}'.format(
            gerrit_user,
            gerrit_host,
            gerrit_port,
            project
        )
        self.message=message

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
            git('remote', 'update')
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
            git('commit', '-m', self.message)
            git('push', 'origin', 'HEAD:refs/for/{0}'.format(self.branch))
        finally:
            os.chdir(curr_dir)


parser = argparse.ArgumentParser()

parser.add_argument('--project', nargs='*')
parser.add_argument('--pattern', default='.*')
parser.add_argument('--branch', default='master')
parser.add_argument('--gerrit-user', default='')
parser.add_argument('--gerrit-host', default='')
parser.add_argument('--gerrit-port', default=29418)
parser.add_argument('--message', default='CI Test Commit')
parser.add_argument('action')

args = parser.parse_args()

valid_actions = ['push', 'recheck', 'abandon-success', 'abandon-failure', 'status']
if args.action not in valid_actions:
    print("Action '{0}' is not valid. Valid actions are: {1}".format(args.action, valid_actions))
    sys.exit(1)

c = GerritClient(gerrit_user=args.gerrit_user,
                 gerrit_host=args.gerrit_host,
                 gerrit_port=args.gerrit_port)

if args.project:
    projects = args.project
else:
    projects = list(c.list_projects(pattern=args.pattern))

status_table = []


for project in projects:
    log.info('\nProject {0}:'.format(project))
    # Recheck existing test commits
    recheck = False
    no_patchsets = True
    for change in c.query("project:{0} branch:{1} message:{2} status:open".format(project,
                          args.branch, args.message.replace(' ', '+'))):
        number = change.get('number', None)
        if number:
            no_patchsets = False
            details = c.details(number, comments=True)
            if details:
                status = details.get('status', None)
                log.debug('status = {0}'.format(status))
                if status == 'NEW':
                    patch_sets = details.get('patchSets', None)
                    if patch_sets:
                        if args.action == 'recheck':
                            log.info("Adding recheck message ...")
                            patchset = patch_sets[-1].get('revision')
                            c.review(revision, message='recheck')
                            recheck = True

                    comments = details.get('comments', None)
                    for comment in reversed(comments):
                        if comment.get('reviewer', {}).get('username') == 'mos-infra-ci':
                            comment_message = comment.get('message', '')
                            if 'FAILURE' in comment_message:
                                status_table.append({
                                    'project': project,
                                    'branch': change['branch'],
                                    'status': 'FAILURE',
                                    'change': change['url'],
                                })
                                if args.action == 'status':
                                    log.info("* patchset '{0}' failed:".format(number))
                                    log.info(comment_message)
                                if args.action == 'abandon-failure':
                                    log.info("* abandoning patchset {0}".format(number))
                                    revision = patch_sets[-1].get('revision')
                                    c.review(revision, abandon=True)
                            else:
                                status_table.append({
                                    'project': project,
                                    'branch': change['branch'],
                                    'status': 'SUCCESS',
                                    'change': change['url'],
                                })
                                if args.action == 'status':
                                    log.info("* patchset '{0}' succeeded.".format(number))
                                if args.action == 'abandon-success':
                                    log.info("* abandoning patchset {0}".format(number))
                                    revision = patch_sets[-1].get('revision')
                                    c.review(revision, abandon=True)
                            break

    if no_patchsets:
        log.info("* no patchsets found")

    if args.action == 'push':
        if not recheck:
            log.info("Pushing test commit ...")
            repo = GerritRepo(project=project,
                              branch=args.branch,
                              message=args.message,
                              gerrit_user=args.gerrit_user,
                              gerrit_host=args.gerrit_host)
            try:
                repo.clone()
                repo.sync()
                repo.testci()
            except:
                log.error('Unable to create test commit for {0}'.format(project))

if args.action == 'status':
    table = PrettyTable(['Project', 'Branch', 'Status', 'Change'])
    table.align['Project'] = 'l'
    for item in status_table:
        table.add_row([item['project'], item['branch'], item['status'], item['change']])
    print table

