import logging

import boto3
import botocore.exceptions


def deploy_stack(stack_name, template_body, resource_types=None, capabilities=None, parameters=None, tags=None,
                 timeout_mins=5):
    logger = logging.getLogger(__name__)
    client = boto3.client('cloudformation')
    create_stack_args = get_create_stack_args(stack_name, template_body, resource_types,
                                              capabilities, parameters, tags, timeout_mins)
    update_stack_args = get_update_stack_args(stack_name, template_body, resource_types,
                                              capabilities, parameters, tags)
    logger.info('Deploying stack: {}'.format(stack_name))
    try:
        stacks = client.describe_stacks(StackName=stack_name)
        stack = stacks['Stacks'][0]
    except botocore.exceptions.ClientError:
        stack = None
    if stack is not None and stack['StackStatus'] in ['CREATE_FAILED']:
        replace_stack(client, stack_name, **create_stack_args)
    elif stack is not None:
        try:
            update_stack(client, stack_name, **update_stack_args)
        except botocore.exceptions.ClientError as ex:
            error_code = ex.response['Error']['Code']
            if error_code == 'ValidationError':
                logger.warning('Validation error: {} (stack={})'.format(ex, stack_name))
            else:
                raise ex
    else:
        create_stack(client, stack_name, **create_stack_args)
    return client.describe_stacks(StackName=stack_name)['Stacks'][0]


def deploy_stack_by_replacement(stack_name, template_body, resource_types=None, capabilities=None, parameters=None,
                                tags=None, timeout_mins=5):
    create_stack_args = get_create_stack_args(
        stack_name, template_body, resource_types, capabilities, parameters, tags, timeout_mins
    )

    logger = logging.getLogger(__name__)
    client = boto3.client('cloudformation')

    logger.info('Deploying stack: {}'.format(stack_name))
    try:
        stacks = client.describe_stacks(StackName=stack_name)
        stack = stacks['Stacks'][0]
    except botocore.exceptions.ClientError:
        stack = None

    if stack is not None:
        replace_stack(client, stack_name, **create_stack_args)
    else:
        create_stack(client, stack_name, **create_stack_args)

    return client.describe_stacks(StackName=stack_name)['Stacks'][0]


def create_stack(client, stack_name, **kwargs):
    logger = logging.getLogger(__name__)
    logger.info('Creating stack: {}'.format(stack_name))
    client.create_stack(**kwargs)
    logger.info('Waiting for stack create to complete: {}'.format(stack_name))
    waiter = client.get_waiter('stack_create_complete')
    waiter.wait(StackName=stack_name)
    logger.info('Stack created: {}'.format(stack_name))


def update_stack(client, stack_name, **kwargs):
    logger = logging.getLogger(__name__)
    logger.info('Updating stack: {}'.format(stack_name))
    client.update_stack(**kwargs)
    logger.info('Waiting for stack update to complete: {}'.format(stack_name))
    waiter = client.get_waiter('stack_update_complete')
    waiter.wait(StackName=stack_name)
    logger.info('Stack updated: {}'.format(stack_name))


def replace_stack(client, stack_name, **kwargs):
    logger = logging.getLogger(__name__)
    logger.info('Replacing stack: {}'.format(stack_name))
    client.delete_stack(StackName=stack_name)
    logger.info('Waiting for stack delete to complete: {}'.format(stack_name))
    waiter = client.get_waiter('stack_delete_complete')
    waiter.wait(StackName=stack_name)
    logger.info('Stack deleted, recreating: {}'.format(stack_name))
    client.create_stack(**kwargs)
    logger.info('Waiting for stack create to complete: {}'.format(stack_name))
    waiter = client.get_waiter('stack_create_complete')
    waiter.wait(StackName=stack_name)
    logger.info('Stack replaced: {}'.format(stack_name))


def get_create_stack_args(stack_name, template_body, resource_types=None, capabilities=None, parameters=None,
                          tags=None, timeout_mins=5):
    return apply_resource_types_to_stack_args(
        apply_capabilities_to_stack_args(
            apply_tags_to_stack_args(
                apply_parameters_to_stack_args(dict(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    DisableRollback=True,
                    TimeoutInMinutes=timeout_mins
                ), parameters), tags), capabilities), resource_types)


def get_update_stack_args(stack_name, template_body, resource_types=None, capabilities=None, parameters=None,
                          tags=None):
    return apply_resource_types_to_stack_args(
        apply_capabilities_to_stack_args(
            apply_tags_to_stack_args(
                apply_parameters_to_stack_args(dict(
                    StackName=stack_name,
                    TemplateBody=template_body
                ), parameters), tags), capabilities), resource_types)


def apply_resource_types_to_stack_args(args, resource_types=None):
    if resource_types is not None:
        args['ResourceTypes'] = resource_types

    return args


def apply_capabilities_to_stack_args(args, capabilities=None):
    if capabilities is not None:
        args['Capabilities'] = capabilities

    return args


def apply_parameters_to_stack_args(args, parameters=None):
    if parameters is not None:
        param_list = [{'ParameterKey': key, 'ParameterValue': parameters[key]} for key in parameters]
        args['Parameters'] = param_list

    return args


def apply_tags_to_stack_args(args, tags=None):
    if tags is not None:
        tag_list = [{'Key': key, 'Value': tags[key]} for key in tags]
        args['Tags'] = tag_list

    return args
