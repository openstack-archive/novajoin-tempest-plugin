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
import exceptions
import subprocess
import time

from oslo_log import log as logging
from tempest import config

from novajoin_tempest_plugin.ipa import ipa_client
from novajoin_tempest_plugin.tests.scenario import manager

CONF = config.CONF
LOG = logging.getLogger(__name__)


class NovajoinScenarioTest(manager.ScenarioTest):

    credentials = ['primary', 'admin']

    def setUp(self):
        super(NovajoinScenarioTest, self).setUp()

    @classmethod
    def setup_credentials(cls):
        cls.set_network_resources()
        super(NovajoinScenarioTest, cls).setup_credentials()

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
        result = self.ipa_client.find_host(host)
        self.assertTrue(result['count'] > 0)

    def verify_host_not_registered_with_ipa(self, host):
        result = self.ipa_client.find_host(host)
        self.assertFalse(result['count'] > 0)

    def verify_host_has_keytab(self, host):
        result = self.ipa_client.show_host(host)['result']
        start = int(time.time())
        keytab_status = result['has_keytab']
        timeout = 300
        while not keytab_status:
            time.sleep(30)
            result = self.ipa_client.show_host(host)['result']
            keytab_status = result['has_keytab']
            if int(time.time()) - start >= 300:
                message = ('Keytab failed to reach TRUE status '
                           'within %s seconds' % (timeout))
                raise exceptions.TimeoutException(message)
        self.assertTrue(keytab_status)

    def verify_service_created(self, service, host, realm):
        service_principal = '{servicename}/{hostname}@{realm}'.format(
            servicename=service, hostname=host, realm=realm
        )
        result = self.ipa_client.find_service(service_principal)
        self.assertTrue(result['count'] > 0)

    def verify_service_managed_by_host(self, service, host, realm):
        # TODO(alee) Implement this using service-show
        pass

    def verify_service_deleted(self, service, host, realm):
        service_principal = '{servicename}/{hostname}@{realm}'.format(
            servicename=service, hostname=host, realm=realm
        )
        result = self.ipa_client.find_service(service_principal)
        self.assertFalse(result['count'] > 0)

    def get_service_cert(self, service, host, realm):
        service_principal = '{servicename}/{hostname}@{realm}'.format(
            servicename=service, hostname=host, realm=realm
        )
        return self.ipa_client.get_service_cert(service_principal)

    def verify_host_is_ipaclient(self, hostip, user, keypair):
        cmd = 'id admin'
        private_key = keypair['private_key']
        ssh_client = self.get_remote_client(hostip, user, private_key)
        result = ssh_client.exec_command(cmd)
        params = ['uid', 'gid', 'groups']
        self.assertTrue(all(x in result for x in params))

    def verify_overcloud_host_is_ipaclient(self, hostip, user):
        keypair = '/home/stack/.ssh/id_rsa'
        cmd = ['ssh', '-i', keypair,
               '{user}@{hostip}'.format(user=user, hostip=hostip),
               '-C', 'id admin']

        result = subprocess.check_output(cmd)
        params = ['uid', 'gid', 'groups']
        self.assertTrue(all(x in result for x in params))

    def verify_cert_tracked(self, hostip, user, keypair, cert_id):
        cmd = 'sudo getcert list -i {certid}'.format(certid=cert_id)
        private_key = keypair['private_key']
        ssh_client = self.get_remote_client(hostip, user, private_key)
        result = ssh_client.exec_command(cmd)
        self.assertTrue('track: yes' in result)

    def verify_overcloud_cert_tracked(self, hostip, user, cert_id):
        keypair = '/home/stack/.ssh/id_rsa'
        cmd = ['ssh', '-i', keypair,
               '{user}@{hostip}'.format(user=user, hostip=hostip),
               '-C', 'sudo getcert list -i {certid}'.format(certid=cert_id)]

        result = subprocess.check_output(cmd)
        self.assertTrue('track: yes' in result)

    def verify_cert_revoked(self, serial):
        # verify that the given certificate has been revoked
        result = self.ipa_client.show_cert(serial)['result']
        self.assertTrue(result['revoked'])

    def verify_compact_services(self, services, host,
                                domain, realm,
                                verify_certs=False):
        for (service, networks) in services.items():
            for network in networks:
                subhost = '{host}.{network}.{domain}'.format(
                    host=host, network=network, domain=domain
                )
                LOG.debug("SUBHOST: %s", subhost)
                self.verify_service(service, subhost, realm,
                                    domain,
                                    verify_certs)

    def verify_service(self, service, host, realm, domain,
                       verify_certs=False):
        self.verify_host_registered_with_ipa(host)
        self.verify_service_created(service, host, realm)
        self.verify_service_managed_by_host(service, host, realm)
        if verify_certs:
            self.verify_service_cert(service, host, realm, domain)

    def verify_service_cert(self, service, host, realm, domain):
        LOG.debug("Verifying cert for %s %s %s", service, host, domain) 
        serial = self.get_service_cert(service, host, realm)
        if (service == 'mysql' and host ==
                'overcloud-controller-0.internalapi.{domain}'.format(
                domain=domain)):
            pass
        else:
            self.assertTrue(serial is not None)

    def verify_managed_services(self, services, realm, domain,
                                verify_certs=False):
        for principal in services:
            service = principal.split('/', 1)[0]
            host = principal.split('/', 1)[1]
            self.verify_service(service, host, realm, domain,
                                verify_certs)
