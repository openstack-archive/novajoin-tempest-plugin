# Copyright 2017 Red Hat
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import base64
from datetime import datetime
from datetime import timedelta
import os

from oslo_log import log as logging
from tempest import config

from novajoin_tempest_plugin import clients
from novajoin_tempest_plugin.tests.scenario import manager as mgr

CONF = config.CONF
LOG = logging.getLogger(__name__)


class NovajoinScenarioTest(mgr.ScenarioTest):

    credentials = ('primary', 'admin')
    manager = clients.Manager()

    def setUp(self):
        super(NovajoinScenarioTest, self).setUp()

    @classmethod
    def skip_checks(cls):
        # check if novajoin is enabled?
        pass

    @classmethod
    def setup_clients(cls):
        super(NovajoinScenarioTest, cls).setup_clients()

        os = getattr(cls, 'os_%s' % cls.credentials[0])
        os_adm = getattr(cls, 'os_%s' % cls.credentials[1])
        # set up ipa client

    def verify_host_registered_with_ipa(self, host):
        # check if specified host is registered with ipa
        # basically doing a host-show
        pass

    def verify_host_not_registered_with_ipa(self, host):
        # check if specified host is not registered with ipa
        pass

    def verify_host_has_keytab(self, host):
        # check if specified host entry has a keytab
        pass

    def verify_host_is_ipaclient(self, host, keypair):
        # ssh into the host
        # do test like "getent passwd admin" or similar
        pass

    def verify_service_created(self, service, host):
        # verify service exists for host on ipa server
        # needed for the triple-O tests
        pass

    def verify_service_deleted(self, servicei, host):
        # verify service entry does not exist
        pass

    def verify_cert_tracked(self, host, keypair, cn):
        # ssh into the host with the provided keypair
        # run certmonger command to ensure cert is
        # being tracked
        pass

   def verify_cert_revoked(self, serial):
       # verify that the given certificate has been revoked
       pass
