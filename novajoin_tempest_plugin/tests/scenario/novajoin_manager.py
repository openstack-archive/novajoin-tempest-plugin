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


from tempest import clients
from tempest.scenario import manager as mgr
from tempest.lib.common import ssh
import tempest.test

class NovajoinScenarioTest(mgr.ScenarioTest):

    credentials = ('primary', 'admin')
    manager = clients.Manager()

    def setUp(self):
        super(NovajoinScenarioTest, self).setUp()
        ssh_host = CONF.tripleo.undercloud_hostname
        ssh_user = CONF.stress.target_ssh_user
        ssh_key = CONF.stress.target_private_key_path
        ssh_client = ssh.Client(ssh_host, ssh_user, key_filename=ssh_key)

    @classmethod
    def skip_checks(cls):
        super(NovajoinScenarioTest, cls).skip_checks()
	cmd = ('source ~/stackrc;openstack service list | grep novajoin')
        novajoin_enabled = ssh_client.exec_command(cmd)
        if not novajoin_enabled:
            raise cls.skipException("Novajoin is not enabled")

    @classmethod
    def setup_clients(cls):
        super(NovajoinScenarioTest, cls).setup_clients()

        # os = getattr(cls, 'os_%s' % cls.credentials[0])
        # os_adm = getattr(cls, 'os_%s' % cls.credentials[1])
        # set up ipa client

    def verify_host_registered_with_ipa(self, host):
        # check if specified host is registered with ipa
        # basically doing a host-show
        
        cmd = 'ipa host-show {hostname}'.format(hostname = host)
        result = ssh_client.exec_command(cmd)
        if host in result:
            return true
        return false

    def verify_host_has_keytab(self, host):
        # check if specified host entry has a keytab

        cmd = 'ipa host-show {hostname} | grep Keytab'.format(hostname = host)
        result = ssh_client.exec_command(cmd)
        if 'True' in result:
            return true
        return false

    def verify_service_exists(self, service, host):
        # verify service exists for host on ipa server
        # needed for the triple-O tests

	cmd = 'ipa service-show {servicename}/{hostname}'.format(
                    servicename=service, hostname=host
                )
        result = ssh_client.exec_command(cmd)
        if service in result:
            return true
        return false

    def verify_host_is_ipaclient(self, host, user, keypair):
        # ssh into the host
        # do test like "getent passwd admin" or similar
        cmd = 'ssh -i {key} {username}@{hostname} -C "id admin"'.format(
                    key=keypair, username=user, hostname=host
                )
        result = ssh_client.exec_command(cmd)
        vars = ['uid', 'gid', 'groups']
        if all(x in result for x in vars):
          return true
        return false

    def verify_cert_tracked(self, host, user, keypair, cn):
        # ssh into the host with the provided keypair
        # run certmonger command to ensure cert is
        # being tracked

        cmd = 'ssh -i {key} {username}@{hostname} -C "sudo getcert list"'.format(
                    key=keypair, username=user, hostname=host
                )
        result = ssh_client.exec_command(cmd)
        if cn in result:
          return true
        return false

    def verify_cert_revoked(self, serial):
        # verify that the given certificate has been revoked
        cmd = 'ipa cert-show {serial} |grep Revoked'.format(
                  serial=serial
               )
        result = ssh_client.exec_command(cmd)
        if 'True' in result:
            return true
        return false
