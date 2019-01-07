# Copyright (c) 2017 Red Hat
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from novajoin_tempest_plugin.tests.scenario import novajoin_manager
from oslo_log import log as logging
from tempest import config

CONF = config.CONF
LOG = logging.getLogger(__name__)

CONTROLLER_CERT_TAGS = [
    'mysql',
    'rabbitmq',
    'httpd-ctlplane',
    'httpd-internal_api',
    'httpd-storage',
    'httpd-storage_mgmt',
    'haproxy-ctlplane-cert',
    'haproxy-external-cert',
    'haproxy-internal_api-cert',
    'haproxy-storage-cert',
    'haproxy-storage_mgmt-cert'
]

COMPUTE_CERT_TAGS = [
    'libvirt-client-cert',
    'libvirt-server-cert'
]


class TripleOTest(novajoin_manager.NovajoinScenarioTest):

    """The test suite for tripleO configuration

    Novajoin is currently deployed in tripleO as part of the
    undercloud as part of a tripleO deployment.

    This test is to validate that all the nodes and services
    for an HA deployment have been correctly created.

    This means:
         * Validating that the undercloud is enrolled in IPA
         * Validating that the controller is enrolled in IPA
         * Validating that the compute node is enrolled
         * Validating that HA services have been created in IPA
         * Validating that certs are being tracked.
         * Validate that TLS connections are being established for
           all internal services
    """

    @classmethod
    def skip_checks(cls):
        super(TripleOTest, cls).skip_checks()
        if not CONF.novajoin.tripleo:
            raise cls.skipException('Tripleo configuration is not enabled')

    def test_hosts_are_registered(self):
        hosts = list(CONF.novajoin.tripleo_controllers)
        hosts.append(CONF.novajoin.tripleo_undercloud)
        hosts.extend(CONF.novajoin.tripleo_computes)
        for host in hosts:
            self.verify_host_registered_with_ipa(host)
            self.verify_host_has_keytab(host)

    def test_verify_compact_services_created(self):
        hosts = list(CONF.novajoin.tripleo_controllers)
        hosts.extend(CONF.novajoin.tripleo_computes)
        for host in hosts:
            metadata = self.servers_client.list_server_metadata(
                self.get_server_id(host))['metadata']
            compact_services = self.get_compact_services(metadata)
            print(compact_services)
            self.verify_compact_services(
                services=compact_services,
                host=host,
                verify_certs=True
            )

    def test_verify_controller_managed_services(self):
        for host in CONF.novajoin.tripleo_controllers:
            metadata = self.servers_client.list_server_metadata(
                self.get_server_id(host))['metadata']
            managed_services = [metadata[key] for key in metadata.keys()
                                if key.startswith('managed_service_')]
            print(managed_services)
            self.verify_managed_services(
                services=managed_services,
                verify_certs=True)

    def test_verify_controller_certs_are_tracked(self):
        for host in CONF.novajoin.tripleo_controllers:
            server_ip = self.get_overcloud_server_ip(host)
            for tag in CONTROLLER_CERT_TAGS:
                self.verify_overcloud_cert_tracked(
                    server_ip,
                    'heat-admin',
                    tag
                )

    def test_verify_compute_certs_are_tracked(self):
        for host in CONF.novajoin.tripleo_computes:
            server_ip = self.get_overcloud_server_ip(host)
            for tag in COMPUTE_CERT_TAGS:
                self.verify_overcloud_cert_tracked(
                    server_ip,
                    'heat-admin',
                    tag
                )

    def test_overcloud_hosts_are_ipaclients(self):
        hosts = list(CONF.novajoin.tripleo_controllers)
        hosts.extend(CONF.novajoin.tripleo_computes)
        for host in hosts:
            server_ip = self.get_overcloud_server_ip(host)
            self.verify_overcloud_host_is_ipaclient(
                server_ip,
                'heat-admin'
            )
