#!/usr/bin/python

import argparse

parser = argparse.ArgumentParser()

parser.add_argument('--file')
parser.add_argument('--key')
parser.add_argument('--column-key')
parser.add_argument('--column-value')
parser.add_argument('--delimiter', default=None)

args = parser.parse_args()

class SafeArray(list):
    def __init__(self, *args, **kwargs):
        super(SafeArray, self).__init__(*args, **kwargs)

    def get(self, index, default=None):
        try:
            return self[index]
        except IndexError:
            return default


class Version(object):
    def __init__(self, string):
        self.raw = string
        self.version = SafeArray()
        self.release = SafeArray()
        self.parse()

    def parse(self):
        a = SafeArray(self.raw.split('-', 1))
        self.version = SafeArray(a.get(0, '').split('.'))
        self.release = SafeArray(a.get(1, '').split('.'))

    def compare(self, version):
        len1 = len(self.version)
        len2 = len(version.version)
        for x in range(0, max(len1, len2)):
            try:
                v1 = int(self.version.get(x, ''))
                v2 = int(version.version.get(x, ''))
            except:
                v1 = str(self.version.get(x, ''))
                v2 = str(version.version.get(x, ''))
            if v1 == v2:
                continue
            elif v1 > v2:
                return 'greater(version)'
            else:
                return 'lower(version)'

        len1 = len(self.release)
        len2 = len(version.release)
        for x in range(0, max(len1, len2)):
            try:
                v1 = int(self.release.get(x, ''))
                v2 = int(version.release.get(x, ''))
            except:
                v1 = str(self.release.get(x, ''))
                v2 = str(version.release.get(x, ''))
            if v1 == v2:
                continue
            elif v1 > v2:
                return 'greater(release)'
            else:
                return 'lower(release)'

        return 'equal'


def split_line(line):
    return line.split(args.delimiter)



result = {}
column_set = set()
with open(args.file, 'r') as f:
    for line in f:
        arr = split_line(line.strip())
        column_set.add(arr[int(args.column_key)])
        result.setdefault(arr[int(args.key)], {}).setdefault(arr[int(args.column_key)], arr[int(args.column_value)])



for key in sorted(result.keys()):
    version = {}
    for repoid in sorted(column_set):
        version[repoid] = Version(result[key].setdefault(repoid, ''))

    if version['updates'].raw:
        result[key]['status'] = version['nailgun'].compare(version['updates'])
    elif version['extras'].raw:
        result[key]['status'] = version['nailgun'].compare(version['extras'])
    elif version['base'].raw:
        result[key]['status'] = version['nailgun'].compare(version['base'])
    else:
        result[key]['status'] = ''



output = []
output.append('key')
for column in sorted(column_set):
    output.append(column)
print ' ; '.join(output)


for key in sorted(result.keys()):
    output = []
    output.append(key)
    for column in sorted(column_set):
        output.append(result[key].setdefault(column, ''))
    output.append(result[key]['status'])
    print ' ; '.join(output)
