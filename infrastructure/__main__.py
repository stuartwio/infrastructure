from openstack import connection
import heatclient.client
import yaml
import json
import os.path
import os
import logging
import sys
import difflib
import openstack.resource2

DEFAULT_CONFIG_PATH = '~/.config/stuartw.io/infrastructure/config.yaml'


class Stack(object):

    def create(self, connection):
        raise NotImplementedError()

    def delete(self, connection):
        raise NotImplementedError()

    def exists(self, connection):
        raise NotImplementedError()

    def fetch(self, connection):
        raise NotImplementedError()

    def update(self, connection):
        raise NotImplementedError()


class UpdateInPlaceDeployment(object):

    def __init__(self, stack):
        self._stack = stack

    def deploy(self, connection):
        if not self._stack.exists(connection):
            self._stack.create(connection)
        else:
            self._stack.update(connection)
        return self._stack.fetch(connection)


class ReplacementDeployment(Stack):

    def __init__(self, stack):
        self._stack = stack

    def deploy(self, connection):
        if self._stack.exists(connection):
            self._stack.delete(connection)
        self._stack.create(connection)
        return self._stack.fetch(connection)


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


class StorageStack(OrchestrationStack):

    def __init__(self):
        super().__init__('seed-storage', 'stacks/storage.yaml')

    def parameters(self, conn):
        return dict()


class ResourcesStack(OrchestrationStack):

    def __init__(self, external_network):
        super().__init__('seed-resources', 'stacks/resources.yaml')
        self.external_network = external_network

    def parameters(self, conn):
        return dict(
            external_network=self.external_network.id
        )


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


def get_file_contents(path):
    with open(path, 'r') as f:
        return f.read()


class DeploymentStack(OrchestrationStack):

    def __init__(self, network_stack, keypair):
        super().__init__('seed-deployment', 'stacks/deployment.yaml')
        self.network_stack = network_stack
        self.keypair = keypair

    @_log_create
    def _create(self, conn, template):
        data = dict(
            stack_name=self.name,
            template=template,
            parameters=self.parameters(conn),
            timeout_mins=self._default_timeout_mins
        )
        heatclient.client.Client('1', session=conn.session).stacks.create(**data)
        return conn.orchestration.find_stack(self.name)

    def parameters(self, conn):
        network = get_output_value(self.network_stack.outputs, 'seed_network')
        cloud_config = "#cloud-config\n{}".format(yaml.dump(dict(
            write_files=[
                dict(
                    path='/var/lib/docker-jenkins/Dockerfile',
                    content=get_file_contents('docker-jenkins/Dockerfile')
                ),
                dict(
                    path='/var/lib/docker-jenkins/plugins.txt',
                    content=get_file_contents('docker-jenkins/plugins.txt')
                ),
                dict(
                    path='/var/lib/docker-jenkins/init.groovy.d/seed.groovy',
                    content=get_file_contents('docker-jenkins/init.groovy.d/seed.groovy')
                ),
                dict(
                    path='/var/lib/docker-jenkins/init.groovy.d/git.groovy',
                    content=get_file_contents('docker-jenkins/init.groovy.d/git.groovy')
                ),
                dict(
                    path='/var/lib/docker-jenkins/init.groovy.d/admin.groovy',
                    content=get_file_contents('docker-jenkins/init.groovy.d/admin.groovy')
                ),
                dict(
                    path='/home/core/.config/seed/auth.json',
                    permissions="0600",
                    owner="core:core",
                    content=get_file_contents('.seed/auth.json')
                ),
                dict(
                    path='/home/core/format-volume.sh',
                    permissions="0700",
                    owner="core:core",
                    content=get_file_contents('instance/scripts/format-volume.sh')
                ),
                dict(
                    path='/home/core/restore-seed-git.sh',
                    permissions="0700",
                    owner="core:core",
                    content=get_file_contents('instance/scripts/restore-seed-git.sh')
                )
            ],
            coreos=dict(
                units=[
                    dict(
                        name='format-volume.service',
                        command='start',
                        content=get_file_contents('instance/systemd/format-volume.service')
                    ),
                    dict(
                        name='media-volume.mount',
                        command='start',
                        content=get_file_contents('instance/systemd/media-volume.mount')
                    ),
                    dict(
                        name='media-volume-home.service',
                        command='start',
                        content=get_file_contents('instance/systemd/media-volume-home.service')
                    ),
                    dict(
                        name='group-jenkins.service',
                        command='start',
                        content=get_file_contents('instance/systemd/group-jenkins.service')
                    ),
                    dict(
                        name='user-jenkins.service',
                        command='start',
                        content=get_file_contents('instance/systemd/user-jenkins.service')
                    ),
                    dict(
                        name='group-git.service',
                        command='start',
                        content=get_file_contents('instance/systemd/group-git.service')
                    ),
                    dict(
                        name='user-git.service',
                        command='start',
                        content=get_file_contents('instance/systemd/user-git.service')
                    ),
                    dict(
                        name='seed-git-repo.service',
                        command='start',
                        content=get_file_contents('instance/systemd/seed-git-repo.service')
                    ),
                    dict(
                        name='ssh-user-jenkins.service',
                        command='start',
                        content=get_file_contents('instance/systemd/ssh-user-jenkins.service')
                    ),
                    dict(
                        name='ssh-git-access.service',
                        command='start',
                        content=get_file_contents('instance/systemd/ssh-git-access.service')
                    ),
                    dict(
                        name='ssh-user-jenkins-git-access.service',
                        command='start',
                        content=get_file_contents('instance/systemd/ssh-user-jenkins-git-access.service')
                    ),
                    dict(
                        name='docker-jenkins-build.service',
                        command='start',
                        content=get_file_contents('instance/systemd/docker-jenkins-build.service')
                    ),
                    dict(
                        name='docker-jenkins-create.service',
                        command='start',
                        content=get_file_contents('instance/systemd/docker-jenkins-create.service')
                    ),
                    dict(
                        name='docker-jenkins.service',
                        command='start',
                        content=get_file_contents('instance/systemd/docker-jenkins.service')
                    )
                ]
            )
        )))

        return dict(
            seed_keypair=self.keypair.name,
            seed_network=network,
            seed_user_data=cloud_config
        )


class AttachmentStack(OrchestrationStack):

    def __init__(self, resource_stack, deployment_stack):
        super().__init__('seed-attachment', 'stacks/attachment.yaml')
        self.resource_stack = resource_stack
        self.deployment_stack = deployment_stack

    def parameters(self, conn):
        return dict(
            seed_ip=get_output_value(self.resource_stack.outputs, 'seed_ip'),
            seed_volume=get_output_value(self.resource_stack.outputs, 'seed_volume'),
            seed_instance=get_output_value(self.deployment_stack.outputs, 'seed_instance')
        )


def readconfig():
    with open(os.path.expanduser(DEFAULT_CONFIG_PATH)) as f:
        return yaml.load(f.read())


def delete_stack(conn, name):
    logger = logging.getLogger(__name__)
    logger.info('Deleting {} stack...'.format(name))
    conn.orchestration.delete_stack(name)
    try:
        openstack.resource2.wait_for_delete(
            conn.session, conn.orchestration.get_stack(name), 2, 150)
    except Exception as ex:
        logger.warning(ex)
    logger.info('{} stack deleted!'.format(name))


def clean(conn):
    delete_stack(conn, 'seed-attachment')
    delete_stack(conn, 'seed-deployment')
    # delete_stack(conn, 'seed-network')
    # delete_stack(conn, 'seed-resources')
    # delete_stack(conn, 'seed-storage')


def deploy(conn):
    external_network = first(conn.network.networks(name='ext-net'))
    storage_stack = StorageStack().apply(conn)
    resource_stack = ResourcesStack(external_network).apply(conn)
    network_stack = NetworkStack(external_network).apply(conn)
    keypair = Keypair('seed').apply(conn)
    deployment_stack = DeploymentStack(network_stack, keypair).apply(conn)
    attachment_stack = AttachmentStack(resource_stack, deployment_stack).apply(conn)


class Opts(object):

    def __init__(self):
        self.identity_api_version='3'

# TODO: Ensure deployment works correctly
# TODO: Set up history between two object storage containers
# TODO: Unit tests

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
    conn = connection.from_config(cloud_name=cloud, options=Opts())

    # token = conn.authorize()
    # print(token)
    # print(conn.authorize())
    # keystone = keystoneclient.v3.client.Client(session=conn.session)
    # result = keystone.tokens.validate(token)
    # print(result)
    #
    # # Before here list
    # seed_git_backup_list_url = '{}/{}'.format(conn.session.get_endpoint(service_type='object-store'), 'seed-git-backups')
    # print(seed_git_backup_list_url)
    # seed_git_backup_url = '{}/{}'.format(conn.session.get_endpoint(service_type='object-store'), 'seed-git-backups/seed-git-backup-latest.tar.gz')

    # user = conn.identity.create_user(
    #     description='The seed instance user.',
    #     default_project_id='44488b6085e6423fbc1e85a1e664a5e4',
    #     domain_id='44488b6085e6423fbc1e85a1e664a5e4',
    #     email='seed@stuartw.io',
    #     name='seed-{}'.format(uuid.uuid4()),
    #     password=uuid.uuid4()
    # )
    # print(user)

    # print(uuid.uuid4())
    #
    # credential = conn.identity.create_credential(
    #     type='ec2',
    #     blob='{"access":"12345","secret":"98765"}',
    #     project_id='44488b6085e6423fbc1e85a1e664a5e4'
    # )
    # print(credential)

    # Upload
    # curl -H 'X-Auth-Token: $auth_token' -H 'Content-Type: application/gzip' -X PUT --data-binary @$file_path $endpoint/$container/$name

    # Download
    # curl -H 'X-Auth-Token: $auth_token' -o $file_path $endpoint/$container/$name

    # List file names
    # curl -H 'X-Auth-Token: $auth_token' $endpoint/$container

    # List file info
    # curl -H 'X-Auth-Token: $auth_token' $endpoint/$container?format=json

    # Latest file (given names are lexically sortable)
    # curl -H 'X-Auth-Token: $auth_token' $endpoint/$container | tail -n 1
    # curl -H 'X-Auth-Token: $auth_token' $endpoint/$container?format=json | jq '.[-1]'

    # If names cannot be used to determine latest
    # curl -H 'X-Auth-Token: $auth_token' $endpoint/$container?format=json | jq 'sort_by(.last_modified)[-1]'

    clean(conn)
    deploy(conn)


if __name__ == '__main__':
    main()
