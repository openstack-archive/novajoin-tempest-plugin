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

import os
import time
import uuid
try:
    from gssapi.exceptions import GSSError
    from ipalib import api
    from ipalib import errors
    from ipalib.install.kinit import kinit_keytab
    ipalib_imported = True
except ImportError:
    # ipalib/ipapython are not available in PyPy yet, don't make it
    # a showstopper for the tests.
    ipalib_imported = False

from oslo_config import cfg
from oslo_log import log as logging
from six.moves.configparser import SafeConfigParser


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class IPABase(object):

    def __init__(self, backoff=0):
        try:
            self.ntries = CONF.connect_retries
        except cfg.NoSuchOptError:
            self.ntries = 1
        if not ipalib_imported:
            return

        try:
            self.keytab = CONF.keytab
        except cfg.NoSuchOptError:
            self.keytab = '/etc/novajoin/krb5.keytab'

        with open(self.keytab):
            pass  # Throw a nicer exception if krb5.keytab does not exist

        self.ccache = "MEMORY:" + str(uuid.uuid4())
        os.environ['KRB5CCNAME'] = self.ccache
        os.environ['KRB5_CLIENT_KTNAME'] = self.keytab
        if self._ipa_client_configured() and not api.isdone('finalize'):
            api.bootstrap(context='novajoin')
            api.finalize()
        self.batch_args = list()
        self.backoff = backoff
        (_hostname, domain, realm) = self.get_host_domain_and_realm()
        self.domain = domain
        self.realm = realm

    def get_host_domain_and_realm(self):
        """Return the hostname and IPA realm name.

           IPA 4.4 introduced the requirement that the schema be
           fetched when calling finalize(). This is really only used by
           the ipa command-line tool but for now it is baked in.
           So we have to get a TGT first but need the hostname and
           realm. For now directly read the IPA config file which is
           in INI format and pull those two values out and return as
           a tuple.
        """
        config = SafeConfigParser()
        config.read('/etc/ipa/default.conf')
        hostname = config.get('global', 'host')
        realm = config.get('global', 'realm')
        domain = config.get('global', 'domain')

        return hostname, domain, realm

    def __backoff(self):
        LOG.debug("Backing off %s seconds", self.backoff)
        time.sleep(self.backoff)
        if self.backoff < 1024:
            self.backoff = self.backoff * 2

    def __get_connection(self):
        """Make a connection to IPA or raise an error."""
        tries = 0

        while (tries <= self.ntries) or (self.backoff > 0):
            if self.backoff == 0:
                LOG.debug("Attempt %d of %d", tries, self.ntries)
            if api.Backend.rpcclient.isconnected():
                api.Backend.rpcclient.disconnect()
            try:
                api.Backend.rpcclient.connect()
                # ping to force an actual connection in case there is only one
                # IPA master
                api.Command[u'ping']()
            except (errors.CCacheError,
                    errors.TicketExpired,
                    errors.KerberosError) as e:
                LOG.debug("kinit again: %s", e)
                # pylint: disable=no-member
                try:
                    kinit_keytab(str('nova/%s@%s' %
                                 (api.env.host, api.env.realm)),
                                 self.keytab,
                                 self.ccache)
                except GSSError as e:
                    LOG.debug("kinit failed: %s", e)
                if tries > 0 and self.backoff:
                    self.__backoff()
                tries += 1
            except errors.NetworkError:
                tries += 1
                if self.backoff:
                    self.__backoff()
            else:
                return

    def _call_ipa(self, command, *args, **kw):
        """Make an IPA call."""
        if not api.Backend.rpcclient.isconnected():
            self.__get_connection()
        if 'version' not in kw:
            kw['version'] = u'2.146'  # IPA v4.2.0 for compatibility

        while True:
            try:
                result = api.Command[command](*args, **kw)
                LOG.debug(result)
                return result
            except (errors.CCacheError,
                    errors.TicketExpired,
                    errors.KerberosError):
                LOG.debug("Refresh authentication")
                self.__get_connection()
            except errors.NetworkError:
                if self.backoff:
                    self.__backoff()
                else:
                    raise

    def _ipa_client_configured(self):
        """Determine if the machine is an enrolled IPA client.

           Return boolean indicating whether this machine is enrolled
           in IPA. This is a rather weak detection method but better
           than nothing.
        """
        return os.path.exists('/etc/ipa/default.conf')


class IPAClient(IPABase):

    def find_host(self, hostname):
        params = [hostname.decode('UTF-8')]
        return self._call_ipa('host_find', *params)

    def show_host(self, hostname):
        params = [hostname.decode('UTF-8')]
        return self._call_ipa('host_show', *params)

    def find_service(self, service_principal):
        params = [service_principal.decode('UTF-8')]
        service_args = {}
        return self._call_ipa('service_find', *params, **service_args)

    def show_service(self, service_principal):
        params = [service_principal.decode('UTF-8')]
        service_args = {}
        return self._call_ipa('service_show', *params, **service_args)

    def get_service_cert(self, service_principal):
        params = [service_principal.decode('UTF-8')]
        service_args = {}
        result = self._call_ipa('service_find', *params, **service_args)
        serviceresult = result['result'][0]
        if 'serial_number' in serviceresult:
            return serviceresult['serial_number']
        else:
            return None

    def service_managed_by_host(self, service_principal, host):
        """Return True if service is managed by specified host"""
        params = [service_principal.decode('UTF-8')]
        service_args = {}
        try:
            result = self._call_ipa('service_show', *params, **service_args)
        except errors.NotFound:
            raise KeyError
        serviceresult = result['result']

        for candidate in serviceresult.get('managedby_host', []):
            if candidate == host:
                return True
        return False

    def host_has_services(self, service_host):
        """Return True if this host manages any services"""
        LOG.debug('Checking if host ' + service_host + ' has services')
        params = []
        service_args = {'man_by_host': service_host}
        result = self._call_ipa('service_find', *params, **service_args)
        return result['count'] > 0

    def show_cert(self, serial_number):
        params = [serial_number]
        return self._call_ipa('cert_show', *params)
