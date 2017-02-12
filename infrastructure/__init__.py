import logging

import yaml

from infrastructure.common.file import File
import infrastructure.providers.aws as aws


class SeedDeployment(object):

    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def deploy(self):
        prefix = 'io-stuartw-seed-test'

        storage_stack_name = '{}-storage'.format(prefix)
        self.log_stack_deployment(storage_stack_name, 'aws')
        storage_stack = aws.deploy_stack(
            stack_name=storage_stack_name.format(prefix),
            template_body=File('stacks/storage.yaml').read(),
            resource_types=['AWS::S3::*'],
            parameters={
                'GitBucketPrefix': prefix
            }
        )
        self.log_stack_deployment_complete(storage_stack)

        resources_stack_name = '{}-resources'.format(prefix)
        self.log_stack_deployment(resources_stack_name, 'aws')
        resources_stack = aws.deploy_stack(
            stack_name=resources_stack_name,
            template_body=File('stacks/resources.yaml').read(),
            resource_types=['AWS::EC2::*']
        )
        self.log_stack_deployment_complete(resources_stack)

        # TODO: Might need to do this as a blue / green deploy
        network_stack_name = '{}-network'.format(prefix)
        self.log_stack_deployment(network_stack_name, 'aws')
        network_stack = aws.deploy_stack(
            stack_name=network_stack_name,
            template_body=File('stacks/network.yaml').read(),
            capabilities=['CAPABILITY_NAMED_IAM']
        )
        self.log_stack_deployment_complete(network_stack)

        deployment_stack_name = '{}-deployment'.format(prefix)
        self.log_stack_deployment(deployment_stack_name, 'aws')
        deployment_stack = aws.deploy_stack_by_replacement(
            stack_name=deployment_stack_name,
            template_body=File('stacks/deployment.yaml').read(),
            capabilities=['CAPABILITY_IAM'],
            parameters={
                'ResourcesStack': resources_stack['StackName'],
                'NetworkStack': network_stack['StackName'],
                'UserData': self.get_cloud_config_init()
            }
        )
        self.log_stack_deployment_complete(deployment_stack)

    def log_stack_deployment(self, stack_name, provider):
        self._logger.info('Deploying: {} (provider={})'.format(stack_name, provider))

    def log_stack_deployment_complete(self, stack):
        self._logger.info(
            'Deployment complete: {} (status={}, created={}, lastupdated={})'.format(
                stack.get('StackName'),
                stack.get('StackStatus'),
                stack.get('CreationTime'),
                stack.get('LastUpdatedTime')))

    @staticmethod
    def get_cloud_config_init():
        return "#cloud-config\n{}".format(yaml.dump(dict(
            coreos=dict(
                units=[
                    dict(
                        name='git-clone.service',
                        command='start',
                        content=File('instance/systemd/git-clone.service').read()
                    ),
                    dict(
                        name='format-volume.service',
                        command='start',
                        content=File('instance/systemd/format-volume.service').read()
                    ),
                    dict(
                        name='home-jenkins.mount',
                        command='start',
                        content=File('instance/systemd/home-jenkins.mount').read()
                    ),
                    dict(
                        name='home-git.mount',
                        command='start',
                        content=File('instance/systemd/home-git.mount').read()
                    ),
                    dict(
                        name='opt-git-ssh.mount',
                        command='start',
                        content=File('instance/systemd/opt-git-ssh.mount').read()
                    ),
                    dict(
                        name='setup-instance.service',
                        command='start',
                        content=File('instance/systemd/setup-instance.service').read()
                    ),
                    dict(
                        name='docker-git.service',
                        command='start',
                        content=File('instance/systemd/docker-git.service').read()
                    ),
                    dict(
                        name='docker-jenkins.service',
                        command='start',
                        content=File('instance/systemd/docker-jenkins.service').read()
                    )
                ]
            )
        )))
