#!/usr/bin/python

import argparse
import re
import json


re_empty_line = re.compile(r'^\s*$')
re_indented_line = re.compile(r'^\s+([^\s].*$)')
re_section_line = re.compile(r'^([A-Za-z\-]+):\s?(.+)$')


def parse_control_file(control_file=None):
    section = None
    output = list()

    if control_file:
        ifile = open(control_file, 'r')
    else:
        raise Exception("No input file provided")

    for line in ifile.readlines():
        line = line.rstrip()
        if re.match(re_empty_line, line):
#            print("# Skipping empty line")
            continue

        match = re.search(re_section_line, line)
        if match:
            p_name = match.group(1)
            p_value = match.group(2)
            if p_name == 'Source' or p_name == 'Package':
                if section:
                    for key, value in section.items():
                        if 'Depends' in key:
                            section[key] = [s.strip() for s in value.split(',')]
                    output.append(section)
                section = dict()
            section[p_name] = p_value
#            print("* Got parameter '{0}' with value '{1}'".format(p_name, p_value))
            continue

        match = re.search(re_indented_line, line)
        if match:
            if p_name == 'Description':
                delim = '\n'
            else:
                delim = ' '
            section[p_name] += delim + match.group(1)
        else:
            print("No match '{0}'".format(line))

    return output


parser = argparse.ArgumentParser()

parser.add_argument('--input-file')

args = parser.parse_args()


if args.input_file:
    print("Processing file {0}".format(args.input_file))
    print(json.dumps(parse_control_file(args.input_file), sort_keys=True, indent=4, separators=(',', ': ')))

