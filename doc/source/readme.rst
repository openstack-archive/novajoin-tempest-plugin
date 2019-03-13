..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

.. _tempest_tests:


Tempest Tests
=============

Novajoin is a Nova metadata service that is used to register newly created
Nova instances with IPA.  This tempest plugin provides tests that validate
that functionality.

The tests are therefore expected to be executed on a node which has been
registered as an IPA client and on which nova is configured to integrate
with novajoin as a metadata server.

In particular, on an OSP13 TripleO deployment that has been configured to use
TLS for both internal and external services, novajoin runs on the undercloud
node.  This means that the undercloud node is registered as an IPA client, and
that the undercloud nova server is configured to retrieve metadata from
novajoin.

It also means that the overcloud controllers and compute nodes are registered
as IPA clients, with the required services and certificates issued.


Setup
-----

This section describes how to set up these tests on an RDO system.

To set up tempest on the RDO system, use dnf to install tempest:

::

    $ sudo dnf install -y openstack-tempest python-devel

Also install the novajoin-tempest-plugin.

::

    $ sudo dnf install python-devel gcc
    $ git clone https://github.com/vakwetu/novajoin_tempest_plugin.git
    $ cd novajoin_tempest_plugin
    $ sudo python setup.py install

Prepare a working directory to run the tempest tests.

::

    $ cd ~
    $ tempest init tempest_run
    $ cd tempest_run

The discovery command detailed below only appears to work for v2 of the
keystone API.  Copy the stackrc file and convert the OS_AUTH_URL to a v2
version.

::

    $ cp /home/stack/stackrc .
    $ vi stackrc (convert to v2 by changing as follows:
      OS_AUTH_URL=https://192.168.24.2:13000/v2.0
      OS_IDENTITY_API_VERSION='2'
    $ source ./stackrc

There is currently a bug in the code used to discover and generate
tempest config files if the volume service (cinder) is not installed.
To work around this, comment out the line:

::

    #check_volume_backup_service(clients.volume_service, conf, services)

at around line 203 in the file
/usr/lib/python2.7/site-packages/config_tempest/config_tempest.py.

Run the discovery command to generate the required tempest config file
under ./etc/tempest.

::

    $ discover-tempest-config --verbose \
      --image http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-x86_64-disk.img \
      --out etc/tempest.conf --debug --create identity.uri $OS_AUTH_URL \
      compute.allow_tenant_isolation true object-storage.operator_role \
      swiftoperator identity.admin_password $OS_PASSWORD

The tests need credentials to connect to the IPA server.  In our tests, we
have used the keytab for the novajoin user.  Copy this keytab and set the
appropriate ownership and permissions for the user executing the plugin.

::

    $ sudo cp /etc/novajoin/krb5.keytab /home/stack/krb5.keytab
    $ sudo chown stack: /home/stack/krb5.keytab

Add the following directives to the [validation] stanza in the generated
tempest configuration file in ./etc/tempest.conf to configure the ssh
client.

::

    $ vi tempest/tempest.conf

       [validation]
       connect_method = fixed
       network_for_ssh = ctlplane


Tempest Configuration
---------------------

The tempest plugin has additional configuration parameters as defined in
./novajoin_tempest_plugin/config.py.

Some of these are described below.  All of these config directives would be
specified under a [novajoin] stanza in ./etc/tempest.conf.

NovajoinGroup = [
    cfg.StrOpt('flavor_tag',
               default='vm',
               help='Flavor tag to use in novajoin enrollment tests'),
    cfg.StrOpt('keytab',
               default='/home/stack/novajoin.keytab',
               help='Keytab to connect to IPA as the novajoin user'),
    cfg.StrOpt('tripleo',
               default='True',
               help='Run triple-O config tests'),
    cfg.ListOpt('tripleo_controllers',
                default=['overcloud-controller-0'],
                help='List of overcloud controller short host names'),
    cfg.ListOpt('tripleo_computes',
                default=['overcloud-novacompute-0'],
                help='List of overcloud compute short host names'),
    cfg.StrOpt('tripleo_undercloud',
               default='undercloud',
               help='Undercloud short host name'
               )

Tempest Configuration for TripleO
---------------------------------

The tempest tests for a tripleo environment are typically run on the
undercloud and use novajoin in the undercloud to generate baremetal nodes
(like the controllers and computes).

In this case, we have made the following tempest configuration work:

::

    [novajoin]
    tripleo_controllers = controller-0,controller-1,controller-2
    tripleo_computes = compute-0,compute-1
    tripleo_undercloud = undercloud-0
    flavor_tag = baremetal

    [validation]
    connect_method = fixed
    network_for_ssh = ctlplane
    image_ssh_user = fedora

    [image]
    image_path = http://foo.example.com/path-to-image.qcow2
    region = regionOne
    http_image = http://foo.example.com/path-to-image.qcow2

Some things to note:

- The flavor_tag is set to either 'vm' or 'baremetal'.  In this case,
  the novajoin enrollment test will try to create test servers on baremetal
  nodes.  This nodes should already be provisioned by ironic.
- The image_path should point to the image to use when creating baremetal
  servers.  The image_ssh_user needs to correspond to the correct default
  user.  For Fedora images, for instance, this is 'fedora'.  Ideally, the
  image should already have the ipa-client package installed.


Running the tests
-----------------

The tests in test_novajoin_enrollment validate that newly created Nova
instances (with the appropriate metadata) are registered with IPA and all
the requested services and hosts are created.  The test also confirms that
the instances and services are appropriately deleted when the instance
is deleted.  To run these tests,

::

    $ tempest run --regex test_novajoin_enrollment

The tests in test_tripleo_deployment should be run on the undercloud in a
TLS enabled tripleo deployment.  These tests verify that the undercloud
and overcloud nodes are registered with IPA and that the required hosts
and services have been created in the IPA server.  In addition, it
confirms that the certificates requested by Heat are tracked by certmonger
on the overcloud nodes.

::

    $ tempest run --regex test_tripleo_deployment

The tests in test_tripleo_tls should be run on the undercloud in a TLS enabled
tripleo deployment.  These tests verify that all services have TLS connections
on all external and internal connections using the openssl client to attempt
TLS connections.

::

    $ tempest run --regex test_tripleo_tls
