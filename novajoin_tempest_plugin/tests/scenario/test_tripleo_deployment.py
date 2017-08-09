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

DOMAIN = 'tripleodomain.example.com'
REALM = 'TRIPLEODOMAIN.EXAMPLE.COM'

HOSTS = [
    'undercloud',
    'overcloud-controller-0'
]

SERVICES = {
    'overcloud-controller-0.ctlplane': ['HTTP'],
    'overcloud-controller-0.internalapi': ['HTTP', 'mysql', 'rabbitmq'],
    'overcloud-controller-0.storage': ['HTTP'],
    'overcloud-controller-0.storagemgmt': ['HTTP'],
    'overcloud.ctlplane': ['haproxy'],
    'overcloud.internalapi': ['haproxy', 'mysql'],
    'overcloud.storage': ['haproxy'],
    'overcloud.storagemgmt': ['haproxy'],
    'overcloud': ['haproxy']
}

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
        pass

    def test_hosts_are_registered(self):
        for host in HOSTS:
            hostname = "{host}.{domain}".format(host=host, domain=DOMAIN)
            self.verify_host_registered_with_ipa(hostname)
            self.verify_host_has_keytab(hostname)

    def test_services_are_created(self):
        self.verify_service_created(
            'nova',
            'undercloud.{domain}'.format(domain=DOMAIN),
            REALM)

        for (host, services) in SERVICES.items():
            subhost = '{host}.{domain}'.format(host=host, domain=DOMAIN)
            self.verify_host_registered_with_ipa(subhost)

            for service in services:
                self.verify_service_created(service, subhost, REALM)
                serial = self.get_service_cert(service, subhost, REALM)

                if (service == 'mysql' and
                        host == 'overcloud-controller-0.internalapi'):
                    pass
                else:
                    self.assertTrue(serial is not None)

    def test_verify_service_certs_are_tracked(self):
        # TODO(alee) get correct overcloud_ip
        overcloud_ip = '192.168.24.17'
        for tag in CONTROLLER_CERT_TAGS:
            self.verify_overcloud_cert_tracked(
                overcloud_ip,
                'heat-admin',
                tag
            )

    def test_overcloud_is_ipaclient(self):
        # TODO(alee) get correct overcloud_ip
        overcloud_ip = '192.168.24.17'
        self.verify_overcloud_host_is_ipaclient(
            overcloud_ip,
            'heat-admin'
        )
