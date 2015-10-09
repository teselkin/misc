__author__ = 'dim'


import subprocess
import re

class ShellCommand():
    def __init__(self, *args, **kwargs):
        self.cmd = []
        self.cmd.extend(args)

    def __call__(self, *args, **kwargs):
        self.process = subprocess.Popen(self.cmd + list(args),
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

        return self.process


def collect_lspci():
    lspci = ShellCommand('lspci')

    arr = []
    d = {}
    for line in lspci('-kvmm').stdout:
        line = line.strip()
        if line == '':
            arr.append(d)
            d = {}
            continue
        kv = re.split('\:\s+', line, maxsplit=1)
        d[kv[0]] = kv[1]
    if len(d.keys()):
        arr.append(d)

    arr2 = []
    d = {}
    for line in lspci('-vv').stdout:
        line = line.strip()
        if line == '':
            arr.append(d)
            d = {}
            continue
        kv = re.split('\:\s+', line, maxsplit=1)
        d[kv[0]] = kv[1]
    if len(d.keys()):
        arr.append(d)

    return arr


def collect_dmidecode():
    dmidecode = ShellCommand('sudo', 'dmidecode')

    data = []
    rec = {}
    rec_no = 0
    last_item = ''
    last_indent = 0
    for line in dmidecode().stdout:
        line = line.rstrip()
        match = re.match(r'Handle ([0x\da-fA-F]+), DMI type ([\da-fA-F]+), (\d+) bytes', line)
        if match:
            if len(rec.keys()):
                data.append(rec)
            rec_no = 1
            rec = {}
            rec['handle'] = match.group(1)
            rec['dmi_type'] = match.group(2)
            rec['size'] = match.group(3)
            last_indent = 1
            last_item = ''
            continue
        if rec_no == 0:
            continue
        if rec_no == 1:
            rec_no = 2
            rec['device_type'] = line
            continue
        rec_no += 1
        indent = line.count('\t', 0, 5)
        if indent > last_indent:
            last_indent = indent
            item = rec[last_item]
            rec[last_item] = []
            if item:
                rec[last_item].append(item)
            rec[last_item].append(line.strip())
            continue
        if indent == 1:
            kv = line.strip().split(':', 1)
            rec[kv[0]] = kv[1].strip()
            last_item = kv[0]
            last_indent = 1
        if indent == 2:
            rec[last_item].append(line.strip())
            continue

    if len(rec.keys()):
        data.append(rec)

    return data


for rec in collect_dmidecode():
    print rec
