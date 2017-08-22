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
import re

from novajoin_tempest_plugin.tests.scenario import novajoin_manager
from oslo_log import log as logging
from tempest import config

CONF = config.CONF
LOG = logging.getLogger(__name__)


class TripleOTLSTest(novajoin_manager.NovajoinScenarioTest):

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
        super(TripleOTLSTest, cls).skip_checks()
        if not CONF.novajoin.tripleo:
            raise cls.skipException('Tripleo configuration is not enabled')

    def get_haproxy_cfg(self, hostip):
        print(hostip)
        return "/home/stack/haproxy.cfg"

    def parse_haproxy_cfg(self, haproxy_file):
        with open(haproxy_file) as f:
            content = f.readlines()
        content = [x.strip() for x in content]

        params = []
        services = {}
        service_tag = None
        for x in content:
            if x.startswith('listen'):
                service_tag = re.search('listen (.*)', x).group(1)
                params = []
            if service_tag is not None:
                if x.startswith('bind'):
                    params.append(x)
                if x.startswith('server'):
                    params.append(x)
                services[service_tag] = params
        return services

    def test_haproxy_tls_connections(self):
        for controller in CONF.novajoin.tripleo_controllers:
            controller_id = self.get_server_id(controller)
            controller_data = self.servers_client.show_server(
                controller_id)['server']
            controller_ip = self.get_server_ip(controller_data)

            haproxy_file = self.get_haproxy_cfg(controller_ip)
            services = self.parse_haproxy_cfg(haproxy_file)

            for tag, params in services.items():
                # TODO(alee) make sure tag/param is not on an exception list
                # if so continue

                print("*** Testing {service}".format(service=tag))
                for param in params:
                    print(param)
                    self.assertTrue("ssl" in param)
                    hostport = self.get_hostport(param)
                    self.verify_overcloud_tls_conn(
                         controller_ip=controller_ip,
                         user='heat-admin',
                         hostport=hostport)

    def get_hostport(self, param):
        if param.startswith("bind"):
            return re.search('bind (\S*) .*', param).group(1)
        if param.startswith('server'):
            return re.search('server (\S*) (\S*) .*', param).group(2)

    def test_rabbitmq_tls_connection(self):
        for controller in CONF.novajoin.tripleo_controllers:
            controller_id = self.get_server_id(controller)
            controller_data = self.servers_client.show_server(
                controller_id)['server']
            controller_ip = self.get_server_ip(controller_data)
            rabbitmq_host = self.get_rabbitmq_host(controller_ip, 'heat-admin')
            rabbitmq_port = self.get_rabbitmq_port(controller_ip, 'heat-admin')
            self.verify_overcloud_tls_conn(
                controller_ip=controller_ip,
                user='heat-admin',
                hostport="{host}:{port}".format(host=rabbitmq_host,
                                                port=rabbitmq_port)
            )
