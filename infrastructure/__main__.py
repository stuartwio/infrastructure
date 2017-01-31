from openstack import connection
import heatclient.client
import yaml
import os.path
import os
import logging
import sys
import difflib
import openstack.resource2

DEFAULT_CONFIG_PATH = '~/.config/stuartw.io/infrastructure/config.yaml'


class Spec(object):

    def apply(self, conn):
        raise NotImplementedError("fetch not implemented")


def first(gen):
    try:
        return next(gen)
    except StopIteration:
        return None


def _log_create(fn):
    def wrapper(self, conn, template):
        self.logger.info('Creating {} stack'.format(self.name))
        result = fn(self, conn, template)
        self.logger.info('{} stack created!\n{}'.format(self.name, result))
        return result
    return wrapper


def _log_get(fn):
    def wrapper(self, conn):
        self.logger.info('Fetching {} stack'.format(self.name))
        result = fn(self, conn)
        self.logger.info('Fetched {} stack!\n{}'.format(self.name, result))
        return result
    return wrapper


def _get_stack_template(conn, stack):
    return heatclient.client.Client('1', session=conn.session).stacks.template(stack)


class OrchestrationStack(Spec):

    _default_timeout_mins = 5

    def __init__(self, name, template, **kwargs):
        self._logger = self._get_logger()
        self.name = name
        self.template = template
        self._kwargs = kwargs

    def parameters(self, conn):
        raise NotImplementedError("properties not implemented")

    @_log_get
    def _get(self, conn):
        return conn.orchestration.find_stack(self.name)

    @_log_create
    def _create(self, conn, template):
        return conn.orchestration.create_stack(
            name=self.name, template=template, parameters=self.parameters(conn),
            timeout_mins=self._default_timeout_mins, **self._kwargs)

    def _read_template(self):
        with open(self.template) as f:
            return yaml.load(f.read())

    def apply(self, conn):
        logger = self._get_logger()
        logger.info('Checking if {} stack exists...'.format(self.name))
        stack = self._get(conn)
        template = self._read_template()
        if stack is None:
            logger.info('{} stack does NOT exist, creating it...'.format(self.name))
            stack = self._create(conn, template)
            openstack.resource2.wait_for_status(conn.session, stack, 'CREATE_COMPLETE', list(), 2, 150)
        else:
            logger.info('{} stack already exists!'.format(self.name))
            stack_template = _get_stack_template(conn, stack.id)
            if stack_template == template:
                logger.info('NO updates required for {}!'.format(self.name))
            else:
                logger.info('Updates required for {}!'.format(self.name))
                difflib.context_diff(template, stack_template)

        return stack

    @property
    def logger(self):
        return self._get_logger()

    @classmethod
    def _get_logger(cls):
        return logging.getLogger('{}.{}'.format(cls.__module__, cls.__name__))


class ResourcesStack(OrchestrationStack):

    def __init__(self):
        super().__init__('seed-resources', 'stacks/resources.yaml')

    def parameters(self, conn):
        return dict()


class NetworkStack(OrchestrationStack):

    def __init__(self, external_network):
        super().__init__('seed-network', 'stacks/network.yaml')
        self.external_network = external_network

    def parameters(self, conn):
        return dict(
            external_network=self.external_network.id
        )


def get_output_value(outputs, key):
    return first(output['output_value'] for output in outputs if output['output_key'] == key)


class Keypair(Spec):

    def __init__(self, name):
        self.name = name

    def apply(self, conn):
        keypair = conn.compute.find_keypair(self.name)
        if keypair is None:
            keypair = conn.compute.create_keypair(name=self.name)

            private_key_path = '{}.pem'.format(self.name)
            public_key_path = '{}.pub'.format(self.name)

            with open(private_key_path, 'w') as private_key_file:
                private_key_file.write(keypair.private_key)
                os.chmod(private_key_path, 0o600)

            with open(public_key_path, 'w') as public_key_file:
                public_key_file.write(keypair.public_key)
                os.chmod(public_key_path, 0o644)

        return keypair


class DeploymentStack(OrchestrationStack):

    def __init__(self, resource_stack, network_stack, keypair):
        super().__init__('seed-deployment', 'stacks/deployment.yaml')
        self.resource_stack = resource_stack
        self.network_stack = network_stack
        self.keypair = keypair

    def parameters(self, conn):

        volume = get_output_value(self.resource_stack.outputs, 'seed_volume')
        network = get_output_value(self.network_stack.outputs, 'seed_network')
        ip = get_output_value(self.network_stack.outputs, 'seed_ip')

        with open('cloud-config.yml', 'r') as f:
            user_data = f.read()

        return dict(
            seed_keypair=self.keypair.name,
            seed_volume=volume,
            seed_network=network,
            seed_ip=ip,
            seed_user_data=user_data
        )


def readconfig():
    with open(os.path.expanduser(DEFAULT_CONFIG_PATH)) as f:
        return yaml.load(f.read())


def clean(conn):

    logger = logging.getLogger(__name__)

    logger.info('Deleting {} stack...'.format('seed-deployment'))
    conn.orchestration.delete_stack('seed-deployment')
    try:
        openstack.resource2.wait_for_delete(conn.session, conn.orchestration.get_stack('seed-deployment'), 2, 150)
    except Exception as ex:
        logger.warning(ex)
    logger.info('{} stack deleted!'.format('seed-deployment'))

    logger.info('Deleting {} stack'.format('seed-network'))
    conn.orchestration.delete_stack('seed-network')
    try:
        openstack.resource2.wait_for_delete(conn.session, conn.orchestration.get_stack('seed-network'), 2, 150)
    except Exception as ex:
        logger.warning(ex)
    logger.info('{} stack deleted!'.format('seed-network'))

    logger.info('Deleting {} stack'.format('seed-resources'))
    conn.orchestration.delete_stack('seed-resources')
    try:
        openstack.resource2.wait_for_delete(conn.session, conn.orchestration.get_stack('seed-resources'), 2, 150)
    except Exception as ex:
        logger.warning(ex)
    logger.info('{} stack deleted!'.format('seed-resources'))


def deploy(conn):

    external_network = first(conn.network.networks(name='ext-net'))
    print(external_network)

    resource_stack = ResourcesStack().apply(conn)
    print(resource_stack)

    network_stack = NetworkStack(external_network).apply(conn)
    print(network_stack)

    keypair = Keypair('seed').apply(conn)
    print(keypair)

    deployment_stack = DeploymentStack(resource_stack, network_stack, keypair).apply(conn)
    print(deployment_stack)


def main():

    root_logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)-15s - %(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    logger = logging.getLogger(__name__)

    config = readconfig()
    cloud = config['os_cloud']

    logger.info('Connecting to cloud {}'.format(cloud))
    conn = connection.from_config(cloud)

    # clean(conn)
    deploy(conn)


if __name__ == '__main__':
    main()
