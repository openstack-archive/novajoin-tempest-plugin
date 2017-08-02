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
