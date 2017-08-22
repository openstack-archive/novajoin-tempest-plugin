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

    def verify_host_registered_with_ipa(self, host, add_domain=True):
        if add_domain:
            host = self.add_domain_to_host(host)
        result = self.ipa_client.find_host(host)
        self.assertTrue(result['count'] > 0)

    def verify_host_not_registered_with_ipa(self, host, add_domain=True):
        if add_domain:
            host = self.add_domain_to_host(host)
        result = self.ipa_client.find_host(host)
        start = int(time.time())
        host_count = result['count']
        timeout = 300
        while (host_count > 0) and (int(time.time()) - start < timeout):
            time.sleep(30)
            result = self.ipa_client.find_host(host)
            host_count = result['count']
        self.assertFalse(result['count'] > 0)

    def add_domain_to_host(self, host):
        host = '{host}.{domain}'.format(
            host=host,
            domain=self.ipa_client.domain)
        return host

    def verify_host_has_keytab(self, host, add_domain=True):
        if add_domain:
            host = self.add_domain_to_host(host)
        result = self.ipa_client.show_host(host)['result']
        start = int(time.time())
        keytab_status = result['has_keytab']
        timeout = 300
        while not keytab_status and (int(time.time()) - start < timeout):
            time.sleep(30)
            result = self.ipa_client.show_host(host)['result']
            keytab_status = result['has_keytab']
        self.assertTrue(keytab_status)

    def verify_service_created(self, service, host):
        service_principal = self.get_service_principal(host, service)
        result = self.ipa_client.find_service(service_principal)
        self.assertTrue(result['count'] > 0)

    def verify_service_managed_by_host(self, service, host):
        service_principal = self.get_service_principal(host, service)
        result = self.ipa_client.service_managed_by_host(service_principal,
                                                         host)
        self.assertTrue(result)

    def verify_service_deleted(self, service, host):
        service_principal = self.get_service_principal(host, service)
        result = self.ipa_client.find_service(service_principal)
        self.assertFalse(result['count'] > 0)

    def verify_compact_services_deleted(self, services, host):
        for (service, networks) in services.items():
            for network in networks:
                subhost = '{host}.{network}.{domain}'.format(
                    host=host, network=network, domain=self.ipa_client.domain
                )
        service_principal = self.get_service_principal(subhost, service)
        result = self.ipa_client.find_service(service_principal)
        self.assertFalse(result['count'] > 0)

    def verify_managed_services_deleted(self, services):
        for principal in services:
            service = principal.split('/', 1)[0]
            host = principal.split('/', 1)[1]
        service_principal = self.get_service_principal(host, service)
        result = self.ipa_client.find_service(service_principal)
        self.assertFalse(result['count'] > 0)

    def get_service_cert(self, service, host):
        service_principal = self.get_service_principal(host, service)
        return self.ipa_client.get_service_cert(service_principal)

    def get_service_principal(self, host, service):
        return '{service}/{hostname}@{realm}'.format(
            service=service, hostname=host, realm=self.ipa_client.realm
        )

    def verify_host_is_ipaclient(self, hostip, user, keypair):
        cmd = "id admin"
        private_key = keypair['private_key']
        ssh_client = self.get_remote_client(hostip, user, private_key)
        result = ssh_client.exec_command(cmd)
        params = ['uid', 'gid', 'groups']
        self.assertTrue(all(x in result for x in params))

    def verify_overcloud_host_is_ipaclient(self, hostip, user):
        cmd = 'id admin'
        result = self.execute_on_controller(user, hostip, cmd)
        params = ['uid', 'gid', 'groups']
        self.assertTrue(all(x in result for x in params))

    def verify_cert_tracked(self, hostip, user, keypair, cert_id):
        cmd = 'sudo getcert list -i {certid}'.format(certid=cert_id)
        private_key = keypair['private_key']
        ssh_client = self.get_remote_client(hostip, user, private_key)
        result = ssh_client.exec_command(cmd)
        self.assertTrue('track: yes' in result)

    def verify_overcloud_cert_tracked(self, hostip, user, cert_id):
        cmd = 'sudo getcert list -i {certid}'.format(certid=cert_id)
        result = self.execute_on_controller(user, hostip, cmd)
        self.assertTrue('track: yes' in result)

    def verify_cert_revoked(self, serial):
        # verify that the given certificate has been revoked
        result = self.ipa_client.show_cert(serial)['result']
        self.assertTrue(result['revoked'])

    def verify_compact_services(self, services, host, verify_certs=False):
        for (service, networks) in services.items():
            for network in networks:
                subhost = '{host}.{network}.{domain}'.format(
                    host=host, network=network, domain=self.ipa_client.domain
                )
                LOG.debug("SUBHOST: %s", subhost)
                self.verify_service(service, subhost, verify_certs)

    def verify_service(self, service, host, verify_certs=False):
        self.verify_host_registered_with_ipa(host, add_domain=False)
        self.verify_service_created(service, host)
        self.verify_service_managed_by_host(service, host)
        if verify_certs:
            self.verify_service_cert(service, host)

    def verify_service_cert(self, service, host):
        LOG.debug("Verifying cert for %s %s", service, host)
        serial = self.get_service_cert(service, host)
        if (service == 'mysql' and host ==
                'overcloud-controller-0.internalapi.{domain}'.format(
                domain=self.ipa_client.domain)):
            pass
        else:
            self.assertTrue(serial is not None)

    def verify_managed_services(self, services, verify_certs=False):
        for principal in services:
            service = principal.split('/', 1)[0]
            host = principal.split('/', 1)[1]
            self.verify_service(service, host, verify_certs)

    def verify_overcloud_tls_connection(self, controller_ip, user, hostport):
        """Check TLS connection.  Failure will raise an exception"""
        cmd = ('echo \'GET / HTTP/1.0\r\n\' | openssl s_client -quiet '
               '-connect {hostport} -tls1_2'.format(hostport=hostport))
        self.execute_on_controller(user, controller_ip, cmd)

    def get_server_id(self, name):
        params = {'all_tenants': '', 'name': name}
        resp = self.servers_client.list_servers(detail=True, **params)
        print(resp)
        links = resp['servers'][0]['links']
        for link in links:
            if link['rel'] == 'self':
                href = link['href']
                return href.split('/')[-1]
        return None

    def get_haproxy_cfg(self, user, controller_ip):
        cmd = 'sudo cat /etc/haproxy/haproxy.cfg'
        return self.execute_on_controller(user, controller_ip, cmd)

    def get_rabbitmq_host(self, user, controller_ip):
        cmd = 'sudo hiera -c /etc/puppet/hiera.yaml rabbitmq::ssl_interface'
        return self.execute_on_controller(user, controller_ip, cmd).rstrip()

    def get_rabbitmq_port(self, user, controller_ip):
        cmd = 'sudo hiera -c /etc/puppet/hiera.yaml rabbitmq::ssl_port'
        return self.execute_on_controller(user, controller_ip, cmd).rstrip()

    def execute_on_controller(self, user, hostip, target_cmd):
        keypair = '/home/stack/.ssh/id_rsa'
        cmd = ['ssh', '-i', keypair,
               '{user}@{hostip}'.format(user=user, hostip=hostip),
               '-C', target_cmd]
        return subprocess.check_output(cmd)
