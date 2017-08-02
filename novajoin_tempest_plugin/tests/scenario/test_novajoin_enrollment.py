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
from tempest.lib import decorators
from tempest import test

from novajoin_tempest_plugin.tests.scenario import novajoin_manager

CONF = config.CONF
LOG = logging.getLogger(__name__)


class EnrollmentTest(novajoin_manager.NovajoinScenarioTest):

    """The test suite for server enrollment

    This test is to verify the enrollment and removal of
    servers with a nova service that has been configured to register
    and de-register clients with an IPA server.

    We create servers using ipa_enroll=True as metadata, and also
    by using an image that contains ipa_enroll=True as metadata.

    The tests do the following:
        * Create a server using either metadata method
        * Validate that the server is registered in the IPA server
        * Validate the the ipaclient is working on the server
        * Delete the newly created server
        * Validate that the server is no longer registered with IPA

    TODO:  We can also add the following tests:
        * Add metadata to register and create some cert entries
        * Validate that the certs for those entries are issued and
          tracked
        * Validate that the service entries are removed when the
          instance is deleted.
        * Validate that the certs issued have been revoked.
    """

    @classmethod
    def skip_checks(cls):
        super(EnrollmentTest, cls).skip_checks()
        pass

    @decorators.idempotent_id('89165fb4-5534-4b9d-8429-97ccffb8f86f')
    @test.services('compute')
    def test_enrollment_using_metadata(self):
        LOG.info("Creating keypair and security group")
        keypair = self.create_keypair()
        security_group = self._create_security_group()
        # TODO(alee) Add metadata for ipa_enroll=True
        # TODO(alee) Add metadata for service to be created/joined

        service = "random service to be added"
        cn = "cn of random service certificate"
        server = self.create_server(
            name='passed_metadata_server',
            image_id=self.no_metadata_img_uuid,
            key_name=keypair['name'],
            security_groups=[{'name': security_group['name']}],
            wait_until='ACTIVE'
        )
        self.verify_registered_host(server, keypair, service, cn)
        self.delete_server(server)

        serial = "serial number of random service certificate"
        self.verify_unregistered_host(server, service, serial)

    @decorators.idempotent_id('cbc752ed-b716-4727-910f-956ccf965723')
    @test.services('compute')
    def test_enrollment_using_image_metadata(self):
        LOG.info("Creating keypair and security group")
        keypair = self.create_keypair()
        security_group = self._create_security_group()

        # TODO(alee) Add metadata for service to be created/joined
        service = "random service to be added"
        cn = "cn of random service certificate"

        server = self.create_server(
            name='img_with_metadata_server',
            image_id=self.metadata_img_uuid,
            key_name=keypair['name'],
            security_groups=[{'name': security_group['name']}],
            wait_until='ACTIVE'
        )
        self.verify_registered_host(server, keypair, service, cn)
        self.delete_server(server)

        serial = "serial number of cert for random service"
        self.verify_unregistered_host(server, service, serial)

    def verify_registered_host(self, server, keypair, service, cn):
        self.verify_host_registered_with_ipa(server)
        self.verify_host_has_keytab(server)
        self.verify_host_is_ipaclient(server, keypair)
        self.verify_service_created(service, server)
        self.verify_cert_tracked(server, keypair, cn)

    def verify_unregistered_host(self, server, service, serial):
        self.verify_host_not_registered_with_ipa(server)
        self.verify_service_deleted(service, server)
        self.verify_cert_revoked(serial)
