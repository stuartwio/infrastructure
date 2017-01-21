from openstack import connection, exceptions
import novaclient.client
import yaml
import os.path
import logging
import sys
from core import Spec, ResourceSpec, Resource
import base64

DEFAULT_CONFIG_PATH = '~/.config/stuartw.io/infrastructure/config.yaml'


def first(gen):
    try:
        return next(gen)
    except StopIteration:
        return None


class ExternalNetworkSpec(ResourceSpec):

    def fetch(self, conn):
        return first(conn.network.networks(name='ext-net'))


class ObjectStoreContainerResourceSpec(ResourceSpec):

    def name(self):
        raise NotImplementedError('name not implemented')

    def fetch(self, conn):
        return first(container for container in conn.object_store.containers() if container.name == self.name())

    def create(self, conn):
        return conn.object_store.create_container(name=self.name())


class GitBackupsContainerSpec(ObjectStoreContainerResourceSpec):

    def name(self):
        return 'git-backups'


class SvnBackupsContainerSpec(ObjectStoreContainerResourceSpec):

    def name(self):
        return 'svn-backups'


class DevelopmentServerVolumeSpec(ResourceSpec):

    _name = 'volume.main.dev.stuartw.io'

    def fetch(self, conn):
        return first(conn.block_store.volumes(name=self._name))

    def create(self, conn):
        return conn.block_store.create_volume(
            name=self._name,
            description='Persistent volume for repositories.',
            size=50
        )


class DevelopmentNetworkSpec(ResourceSpec):

    _name = 'dev.stuartw.io'

    def fetch(self, conn):
        return first(conn.network.networks(name=self._name))

    def create(self, conn):
        return conn.network.create_network(
            name=self._name
        )


class DevelopmentSubnetSpec(ResourceSpec):

    # Removing extra subnets as we don't appear to have zones
    # i.e. privately networked intra-region datacentre locations
    # in City Cloud. If we start to care more about disaster
    # recovery, we can do same geography region high-availability.

    _cidr = dict(
        a='10.0.1.0/24'
    )

    _gateway_id = dict(
        a='10.0.1.1'
    )

    _name_template = '{}.subnet.dev.stuartw.io'

    def __init__(self, suffix):
        self._suffix = suffix
        self._network_spec = DevelopmentNetworkSpec()
        self._router_spec = DevelopmentRouterSpec()

    def fetch(self, conn):
        return first(conn.network.subnets(name=self._name_template.format(self._suffix)))

    def create(self, conn):
        network = self._network_spec.apply(conn)
        router = self._router_spec.apply(conn)
        subnet = conn.network.create_subnet(
            name=self._name_template.format(self._suffix),
            network_id=network.id,
            ip_version='4',
            cidr=self._cidr[self._suffix],
            gateway_id=self._cidr[self._suffix]
        )
        conn.network.add_interface_to_router(router, subnet.id)
        return subnet


class DevelopmentRouterSpec(ResourceSpec):

    _name = 'router.dev.stuartw.io'

    def __init__(self):
        self._external_network_spec = ExternalNetworkSpec()

    def fetch(self, conn):
        return first(conn.network.routers(name=self._name))

    def create(self, conn):
        return conn.network.create_router(
            name=self._name,
            external_gateway_info=dict(
                network_id=self._external_network_spec.apply(conn).id
            )
        )


class DevelopmentServerKeyPairSpec(ResourceSpec):

    name = 'stuartwiodev'

    def fetch(self, conn):
        try:
            return conn.compute.get_keypair(self.name)
        except exceptions.ResourceNotFound:
            return None

    def create(self, conn):
        key_pair = conn.compute.create_keypair(name=self.name)

        with open(os.path.join(os.getcwd(), '{}.pub'.format(self.name)), 'w') as f:
            f.write(key_pair.public_key)

        with open(os.path.join(os.getcwd(), '{}.pem'.format(self.name)), 'w') as f:
            f.write(key_pair.private_key)

        return key_pair


class DevelopmentServerSpec(ResourceSpec):

    _name = 'main.dev.stuartw.io'

    def fetch(self, conn):
        server = conn.compute.find_server(self._name)
        return None if server is None else conn.compute.wait_for_server(server)

    def create(self, conn):
        logger = self.getlogger()

        network = DevelopmentNetworkSpec().apply(conn)
        volume = DevelopmentServerVolumeSpec().apply(conn)
        flavor = conn.compute.find_flavor('1C-1GB')
        image = conn.compute.find_image('CoreOS 1068.9.0')
        keypair = DevelopmentServerKeyPairSpec().name

        with open('cloud-config.yml') as f:
            userdata = base64.b64encode(f.read().encode()).decode('utf-8')

        logger.info('----- BEGIN USERDATA -----')
        logger.info(userdata)
        logger.info('----- END USERDATA -----')

        logger.info('Creating server with flavor {} and image {}'.format(flavor.name, image.name))
        server = conn.compute.create_server(
            name=self._name,
            key_name=keypair,
            flavor_id=flavor.id,
            image_id=image.id,
            networks=[
                dict(
                    uuid=network.id
                )
            ],
            user_data=userdata
        )
        logger.info('Building server {}...'.format(server.id))
        server = conn.compute.wait_for_server(server)
        logger.info('Server built!')

        logger.info('Attaching volume {} to server {}'.format(volume.id, server.id))
        client = novaclient.client.Client('2.1', session=conn.session)
        volume = client.volumes.create_server_volume(server.id, volume.id)
        logger.info('Volume attached {}'.format(volume.id))

        return server

    @classmethod
    def getlogger(cls):
        return logging.getLogger(cls.__name__)


class DevelopmentServerFloatingIpSpec(ResourceSpec):

    def fetch(self, conn):
        server = DevelopmentServerSpec().apply(conn)
        port = first(conn.network.ports(device_id=server.id))
        ip = conn.network.ips(port_id=port.id)
        return first(ip)

    def create(self, conn):
        server = DevelopmentServerSpec().apply(conn)
        port = first(conn.network.ports(device_id=server.id))
        return conn.network.create_ip(
            port_id=port.id,
            floating_network_id=ExternalNetworkSpec().apply(conn).id
        )


class StorageStackSpec(Spec):

    def apply(self, conn):
        return StorageStackResource(
            git_backups_container=GitBackupsContainerSpec().apply(conn),
            svn_backups_container=SvnBackupsContainerSpec().apply(conn),
            development_server_volume=DevelopmentServerVolumeSpec().apply(conn)
        )


class StorageStackResource(Resource):

    def __init__(self, git_backups_container, svn_backups_container, development_server_volume):
        self.git_backups_container = git_backups_container
        self.svn_backups_container = svn_backups_container
        self.development_server_volume = development_server_volume


class DevelopmentNetworkStackSpec(Spec):

    def __init__(self):
        self._network_spec = DevelopmentNetworkSpec()
        self._router_spec = DevelopmentRouterSpec()
        self._subnet_a_spec = DevelopmentSubnetSpec('a')

    def apply(self, conn):
        return DevelopmentNetworkStackResource(
            network=self._network_spec.apply(conn),
            router=self._router_spec.apply(conn),
            subnet_a=self._subnet_a_spec.apply(conn)
        )


class DevelopmentNetworkStackResource(Resource):

    def __init__(self, network, router, subnet_a):
        self.network = network
        self.router = router
        self.subnet_a = subnet_a


class DevelopmentServerStackSpec(Spec):

    def __init__(self):
        self._key_pair_spec = DevelopmentServerKeyPairSpec()
        self._server_spec = DevelopmentServerSpec()
        self._floating_ip_spec = DevelopmentServerFloatingIpSpec()

    def apply(self, conn):
        return DevelopmentServerStackResource(
            key_pair=self._key_pair_spec.apply(conn),
            server=self._server_spec.apply(conn),
            floating_ip=self._floating_ip_spec.apply(conn)
        )


class DevelopmentServerStackResource(Resource):

    def __init__(self, key_pair, server, floating_ip):
        self.key_pair = key_pair
        self.server = server
        self.floating_ip = floating_ip


def readconfig():
    with open(os.path.expanduser(DEFAULT_CONFIG_PATH)) as f:
        return yaml.load(f.read())


def main():

    logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)-15s - %(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    config = readconfig()
    cloud = config['os_cloud']

    logger.info('Connecting to cloud {}'.format(cloud))
    conn = connection.from_config(cloud)

    logger.info('Verifying storage stack...')
    storage_stack = StorageStackSpec().apply(conn)
    logger.info('Storage stack {}'.format(storage_stack))

    logger.info('Verifying development network stack...')
    development_network_stack = DevelopmentNetworkStackSpec().apply(conn)
    logger.info('Development network stack {}'.format(development_network_stack))

    logger.info('Verifying development server stack...')
    development_server_stack = DevelopmentServerStackSpec().apply(conn)
    logger.info('Development server stack {}'.format(development_server_stack))

if __name__ == '__main__':
    main()
