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
from oslo_log import log as logging
from tempest import config
from tempest import test

from novajoin_tempest_plugin.ipa import ipa_client
CONF = config.CONF
LOG = logging.getLogger(__name__)


class NovajoinScenarioTest(test.BaseTestCase):
    def setUp(self):
        super(NovajoinScenarioTest, self).setUp()

    @classmethod
    def skip_checks(cls):
        super(NovajoinScenarioTest, cls).skip_checks()
        if not CONF.service_available.novajoin:
            raise cls.skipException("Novajoin is not enabled")

    @classmethod
    def setup_clients(cls):
        super(NovajoinScenarioTest, cls).setup_clients()
        cls.ipa_client = ipa_client.IPAClient()

    def verify_host_registered_with_ipa(self, host):
        # check if specified host is registered with ipa
        # basically doing a host-show
        result = self.ipa_client.find_host(host)
        if result['count'] > 0:
            return True
        return False

    def verify_host_has_keytab(self, host):
        # check if specified host entry has a keytab
        result = self.ipa_client.show_host(host)['result']
        keytab_present = result['Keytab']
        if 'True' in keytab_present:
            return True
        return False

    def verify_service_exists(self, service, host):
        # verify service exists for host on ipa server
        # needed for the triple-O tests
        service_principal = '{servicename}/{hostname}'.format(
            servicename=service, hostname=host
        )
        result = self.ipa_client.find_service(service_principal)
        if result['count'] > 0:
            return True
        return False

    def verify_host_is_ipaclient(self, host, user, keypair):
        # ssh into the host
        # do test like "getent passwd admin" or similar
        cmd = 'ssh -i {key} {username}@{hostname} -C "id admin"'.format(
            key=keypair, username=user, hostname=host
        )
        result = self.ssh_client.exec_command(cmd)
        params = ['uid', 'gid', 'groups']
        if all(x in result for x in params):
            return True
        return False

    def verify_cert_tracked(self, host, user, keypair, cn):
        # ssh into the host with the provided keypair
        # run certmonger command to ensure cert is
        # being tracked

        cmd = (
            'ssh -i {key} {username}@{hostname} -C "sudo getcert list"'.format(
                key=keypair, username=user, hostname=host)
        )
        result = self.ssh_client.exec_command(cmd)
        if cn in result:
            return True
        return False

    def verify_cert_revoked(self, serial):
        # verify that the given certificate has been revoked
        result = self.ipa_client.show_cert(serial)['result']
        is_revoked = result['Revoked']
        if 'True' in is_revoked:
            return True
        return False
