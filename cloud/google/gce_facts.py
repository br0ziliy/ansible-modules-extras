#!/usr/bin/python
# -*- coding: utf-8 -*-

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: gce_facts
short_description: Gathers facts about instances within Google Cloud infrastructure
version_added: "1.0"
options:
description:
     - This module fetches data from the metadata servers in Google Cloud as per
       https://cloud.google.com/compute/docs/metadata.
       The module must be called from within the GCE instance itself.
       Module based on the code written by Silviu Dicu <silviudicu@gmail.com>.
author: "Vasiliy Kaygorodov <vkaygorodov@gmail.com>"
'''

EXAMPLES = '''
# To see the list of all the facts use command below:

$ ansible -m gce_facts all

# Conditional playbook example
- name: Gather instance GCE facts
  action: gce_facts

- name: Conditional
  action: debug msg="This instance is scheduled to restart automatically"
  when: ansible_gce.instance.scheduling.automaticRestart == "TRUE"
'''

class GceMetadata(object):

    gce_metadata_uri = 'http://metadata.google.internal/computeMetadata/v1/?recursive=True'

    def __init__(self, module, gce_metadata_uri=None):
        self.module   = module
        self.uri_meta = gce_metadata_uri or self.gce_metadata_uri
        self._data     = { 'ansible_gce': {} }

    def _fetch(self, url):
        (response, info) = fetch_url(self.module, url, headers={ "Metadata-Flavor": "Google" }, force=True)
        if response:
            data = response.read()
        else:
            data = None
        self._data['ansible_gce'] = self.module.from_json(data)

    def _mangle_data(self, data):
        """
        Perform some keys conversion to make things look prettier.
        Example: "projects/11111111111/zones/us-central1-b" becomes "us-central1-b"
        Also process project sshKeys string and convert it to a list.
        """
        machine_type = data['ansible_gce']['instance']['machineType'].split('/')[3]
        zone = data['ansible_gce']['instance']['zone'].split('/')[3]
        data['ansible_gce']['instance']['machineType'] = machine_type
        data['ansible_gce']['instance']['zone'] = zone
        for interface in data['ansible_gce']['instance']['networkInterfaces']:
            network = interface['network'].split('/')[3]
            interface['network'] = network
        ssh_keys = data['ansible_gce']['project']['attributes']['sshKeys']
        data['ansible_gce']['project']['attributes']['sshKeys'] = []
        for ssh_key in ssh_keys.split('\n'):
            data['ansible_gce']['project']['attributes']['sshKeys'].append(ssh_key)
        return data

    def run(self):
        self._fetch(self.uri_meta) # populate _data
        data = self._mangle_data(self._data)
        return data

def main():
    argument_spec = url_argument_spec()

    module = AnsibleModule(
        argument_spec = argument_spec,
        supports_check_mode = True,
    )

    gce_facts = GceMetadata(module).run()
    gce_facts_result = dict(changed=False, ansible_facts=gce_facts)

    module.exit_json(**gce_facts_result)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.urls import *

main()
