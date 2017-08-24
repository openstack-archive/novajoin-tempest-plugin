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

from oslo_log import log as logging

from tempest import config
from tempest.lib.common.utils import data_utils

from novajoin_tempest_plugin.tests.scenario import novajoin_manager

import ast

CONF = config.CONF
LOG = logging.getLogger(__name__)
USER = 'cloud-user'
NETWORK = 'ctlplane'


class ServerTest(novajoin_manager.NovajoinScenarioTest):

    credentials = ['primary', 'admin']

    @classmethod
    def setup_credentials(cls):
        cls.set_network_resources()
        super(ServerTest, cls).setup_credentials()

    @classmethod
    def setup_clients(cls):
        super(ServerTest, cls).setup_clients()

    @classmethod
    def resource_setup(cls):
        super(ServerTest, cls).resource_setup()

    def _create_flavor(self, flavor_name):
        specs = {"capabilities:boot_option": "local",
                 "capabilities:profile": "compute"}
        flv_id = data_utils.rand_int_id(start=1000)
        ram = 4096
        vcpus = 1
        disk = 40
        self.flavors_client.create_flavor(name=flavor_name,
                                          ram=ram,
                                          vcpus=vcpus,
                                          disk=disk,
                                          id=flv_id)['flavor']
        self.flavors_client.set_flavor_extra_spec(flv_id,
                                                  **specs)
        return flv_id

    def _create_image(self, name, properties={}):
        container_format = 'bare'
        disk_format = 'qcow2'
        image_id = self.image_create(name=name,
                                     fmt=container_format,
                                     disk_format=disk_format,
                                     properties=properties)
        return image_id

    def _verify_host_and_services_are_enrolled(
            self, server_name, server_id, keypair):
        self.verify_host_registered_with_ipa(server_name)
        self.verify_host_has_keytab(server_name)

        # Verify compact services are created

        metadata = self.servers_client.list_server_metadata(server_id
                                                            )['metadata']
        services = metadata['compact_services']
        self.compact_services = ast.literal_eval(services)
        self.verify_compact_services(
            services=self.compact_services,
            host=server_name,
        )

        # Verify managed services are created
        self.managed_services = [metadata[key] for key in metadata.keys()
                                 if key.startswith('managed_service_')]
        self.verify_managed_services(self.managed_services)

        # Verify instance created above is ipaclient
        server_details = self.servers_client.show_server(server_id
                                                         )['server']
        ip = self.get_server_ip(server_details)
        self.verify_host_is_ipaclient(ip, USER, keypair)

    def _verify_host_and_services_are_not_enrolled(self, server_name):
        # Verify host and associated compact and managed services
        # are no longer registered with ipa
        self.verify_host_not_registered_with_ipa(server_name)
        self.verify_compact_services_deleted(services=self.compact_services,
                                             host=server_name)
        self.verify_managed_services_deleted(self.managed_services)

    def test_enrollment_metadata_in_instance(self):

        networks = self.networks_client.list_networks(name=NETWORK)
        net_id = networks['networks'][0]['id']
        flavor_name = data_utils.rand_name('flv_metadata_in_instance')
        flavor_id = self._create_flavor(flavor_name)
        image_name = data_utils.rand_name('img_metadata_in_instance')
        image_id = self._create_image(image_name)
        keypair = self.create_keypair()
        instance_name = data_utils.rand_name("instance")
        metadata = {"ipa_enroll": "True",
                    "compact_services":
                    "{\"HTTP\": [\"ctlplane\", \"internalapi\"]}",
                    "managed_service_test": "novajoin/test.example.com"}
        server = self.create_server(name=instance_name,
                                    image_id=image_id,
                                    flavor=flavor_id,
                                    net_id=net_id,
                                    key=keypair['name'],
                                    metadata=metadata,
                                    wait_until='ACTIVE')
        self._verify_host_and_services_are_enrolled(instance_name,
                                                    server['id'],
                                                    keypair)
        self.servers_client.delete_server(server['id'])
        self._verify_host_and_services_are_not_enrolled(instance_name)

    def test_enrollment_metadata_in_image(self):

        networks = self.networks_client.list_networks(name=NETWORK)
        net_id = networks['networks'][0]['id']
        flavor_name = data_utils.rand_name('flv_metadata_in_image')
        flavor_id = self._create_flavor(flavor_name)
        image_name = data_utils.rand_name('metadata_in_image')
        properties = {"ipa_enroll": "True"}
        image_id = self._create_image(image_name, properties)
        keypair = self.create_keypair()
        f = open('/tmp/priv.key', 'w')
        f.write(keypair['private_key'])
        f.close()
        instance_name = data_utils.rand_name("novajoin")
        metadata = {"compact_services":
                    "{\"HTTP\": [\"ctlplane\", \"internalapi\"]}",
                    "managed_service_test": "novajoin/test.example.com"}
        server = self.create_server(name=instance_name,
                                    image_id=image_id,
                                    flavor=flavor_id,
                                    net_id=net_id,
                                    key=keypair['name'],
                                    metadata=metadata,
                                    wait_until='ACTIVE')
        self._verify_host_and_services_are_enrolled(instance_name,
                                                    server['id'], keypair)
        self.servers_client.delete_server(server['id'])
        self._verify_host_and_services_are_not_enrolled(instance_name)
