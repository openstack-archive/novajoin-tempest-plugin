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

TLS_EXCEPTIONS = [
    ("nova_novncproxy", "6080"),
    ("redis", "6379"),
    ("nova_metadata", "8775"),
    ("mysql", "3306"),
    ("haproxy.stats", "1993"),
    ("horizon", "80")
]


class TripleOTLSTest(novajoin_manager.NovajoinScenarioTest):

    """The test suite for tripleO configuration

    Novajoin is currently deployed in tripleO as part of the
    undercloud as part of a tripleO deployment.

    This test is to validate that all the nodes and services
    for an HA deployment have been correctly created.

    This means:
        * Validate that all haproxy services can be connected
          using openssl client (tls)
        * Validate rabbitmq can be connected using TLS.
    """

    @classmethod
    def skip_checks(cls):
        super(TripleOTLSTest, cls).skip_checks()
        if not CONF.novajoin.tripleo:
            raise cls.skipException('Tripleo configuration is not enabled')

    def get_haproxy_cfg_1(self, hostip):
        print(hostip)
        return "/home/stack/haproxy.cfg"

    def parse_haproxy_cfg(self, haproxy_data):
        content = haproxy_data.splitlines()
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
            controller_ip = self.get_overcloud_server_ip(controller)
            haproxy = self.get_haproxy_cfg('heat-admin', controller_ip)
            services = self.parse_haproxy_cfg(haproxy)

            for tag, params in services.items():
                print("*** Testing {service}".format(service=tag))
                for param in params:
                    print(param)
                    hostport = self.get_hostport(param)
                    port = re.search('\S*:(\d*)', hostport).group(1)
                    if "ssl" not in param:
                        if (tag, port) in TLS_EXCEPTIONS:
                            print("Exception: {p}".format(p=param))
                        continue

                    self.assertTrue("ssl" in param)
                    self.verify_overcloud_tls_connection(
                        controller_ip=controller_ip,
                        user='heat-admin',
                        hostport=hostport
                    )

    def get_hostport(self, param):
        if param.startswith("bind"):
            return re.search('bind (\S*) .*', param).group(1)
        if param.startswith('server'):
            return re.search('server (\S*) (\S*) .*', param).group(2)

    def test_rabbitmq_tls_connection(self):
        for controller in CONF.novajoin.tripleo_controllers:
            controller_ip = self.get_overcloud_server_ip(controller)
            rabbitmq_host = self.get_rabbitmq_host('heat-admin', controller_ip)
            rabbitmq_port = self.get_rabbitmq_port('heat-admin', controller_ip)
            self.verify_overcloud_tls_connection(
                controller_ip=controller_ip,
                user='heat-admin',
                hostport="{host}:{port}".format(host=rabbitmq_host,
                                                port=rabbitmq_port)
            )

    def test_libvirt_tls_connection(self):
        for compute in CONF.novajoin.tripleo_computes:
            compute_ip = self.get_overcloud_server_ip(compute)
            libvirt_port = self.get_libvirt_port('heat-admin', compute_ip)

            # TODO(alee) Is the host correct?
            self.verify_overcloud_tls_connection(
                controller_ip=compute_ip,
                user='heat-admin',
                hostport="{host}:{port}".format(host=compute_ip,
                                                port=libvirt_port)
            )
