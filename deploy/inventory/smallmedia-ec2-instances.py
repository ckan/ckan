#!/usr/bin/env python

"""
This script uses your boto/awscli AWS access key to query the list of *running*
instances in eu-west-1, dynamically producing Ansible hosts and groups to
match.

The latest copy of this script is located at:

    https://github.com/smallmedia/infrastructure/blob/master/inventory/smallmedia-ec2-instances.py

For usage instructions, please see:

    https://github.com/smallmedia/infrastructure/blob/master/docs/ansible-dynamic-inventory.md
"""

import json
import logging
import re
import sys

from pprint import pprint

import boto.ec2


NAME_RE = '^[a-z][a-z0-9-]{1,32}-(staging|live|test)$'
PROJECT_RE = '^[a-z][a-z0-9-]{1,32}$'
VALID_ENVS = ['staging', 'live']

IAM_PROFILE_FOR_ENV = {
    'staging': '', # 'arn:aws:iam::229340663981:instance-profile/smallmedia-staging-vm',
    'live': 'arn:aws:iam::229340663981:instance-profile/smallmedia-production-vm',
}

def main():
    logging.basicConfig(level=logging.WARNING,
                        stream=open('/dev/tty', 'w', 1),
                        format="smallmedia-ec2-instances.py: %(message)s")

    ec2 = boto.ec2.connect_to_region('eu-west-1')
    reservations = ec2.get_all_instances()
    instances = [i for r in reservations for i in r.instances]

    output = {
        '_meta': {
            'hostvars': {
            }
        }
    }

    seen_names = {}

    for instance in instances:
        env = instance.tags.get('Environment', '').encode('ascii')
        name = instance.tags.get('Name', '').encode('ascii')
        project = instance.tags.get('Project', '').encode('ascii')
        profile_arn = (instance.instance_profile or {}).get('arn', '')

        if env not in VALID_ENVS:
            logging.warn(
                'Instance %s (%r) has invalid Environment tag %r, must be one of %s',
                instance.id,
                name,
                env,
                ', '.join(sorted(VALID_ENVS))
            )
            continue

        if not re.match(NAME_RE, name):
            logging.warn(
                'Instance %s has invalid Name tag %r, must match %s',
                instance.id,
                name,
                NAME_RE
            )
            continue

        if instance.state != 'running':
            continue

        if name in seen_names:
            logging.warn(
                'Instance %s has duplicate Name tag %r, already belongs to %r',
                instance.id,
                name,
                seen_names[name],
            )
            continue

        seen_names[name] = instance.id

        if not re.match(PROJECT_RE, project):
            logging.warn(
                'Instance %s (%s) has invalid Project tag %r, must match %s',
                instance.id,
                name,
                project,
                PROJECT_RE
            )
            continue

        if profile_arn != IAM_PROFILE_FOR_ENV[env]:
            logging.warn(
                'Instance %s (%s) has invalid IAM ARN %r, must be %r',
                instance.id,
                name,
                profile_arn,
                IAM_PROFILE_FOR_ENV[env],
            )
            continue

        group_names = (
            env,
            'ec2',
            'ec2-%s' % (project,),
            'ec2-%s' % (env,),
            'ec2-%s-%s' % (project, env),
        )

        output['_meta']['hostvars'][name] = {
            'ansible_host': instance.ip_address,
            'ec2': {
                'instance_id': instance.id,
                'private_ip_address': instance.private_ip_address,
                'environment': env,
                'project': project,
                'name': name,
                'groups': list(group_names),
            }
        }

        for group_name in group_names:
            group = output.setdefault(group_name, {
                'hosts': [],
                'vars': {}
            })

            group['hosts'].append(name)

    json.dump(obj=output,
              fp=sys.stdout,
              sort_keys=True,
              indent=4)

if __name__ == '__main__':
    main()
