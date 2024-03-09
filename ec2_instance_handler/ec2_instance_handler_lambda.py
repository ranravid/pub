import boto3
from datetime import datetime, timedelta, timezone


def check_root_volume_created_within_last_24_hours(instance_id: str) -> bool:
    """Check the instance root volume was created within the last 24 hours."""
    boto3.client('sts').get_caller_identity().get('Account')
    ec2_client = boto3.client('ec2')
    volumes = ec2_client.describe_volumes(Filters=[{'Name': 'attachment.instance-id', 'Values': [instance_id]}])['Volumes']

    if volumes:
        root_volume_create_time = volumes[0]['CreateTime']
        creation_time = datetime.strptime(str(root_volume_create_time), "%Y-%m-%d %H:%M:%S.%f%z")
        current_time = datetime.now(timezone.utc)
        time_difference = current_time - creation_time
        return time_difference < timedelta(hours=24)
    else:
        return False


def stop_instances(instance_ids: [str]) -> object:
    ec2_client = boto3.client('ec2')
    ec2_client.stop_instances(InstanceIds=instance_ids)


def terminate_instances(instance_ids: [str]) -> object:
    ec2_client = boto3.client('ec2')
    ec2_client.modify_instance_attribute(InstanceId=instance_ids, DisableApiTermination={'Value': False})
    ec2_client.terminate_instances(InstanceIds=instance_ids)


def get_instance_ids_by_tags(tags_dict: dict):
    """Get a list of instance ids by specific dictionary of tags."""
    ec2_client = boto3.client('ec2')
    filters = [{'Name': f'tag:{tag_key}', 'Values': [tag_value]} for tag_key, tag_value in tags_dict.items()]
    response = ec2_client.describe_instances(Filters=filters)
    instance_ids = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
    return instance_ids


# Lambda Handler
def lambda_handler(event, context):
    tags = {
        'env': 'dev',
        'lifecycle': 'temporary'
    }

    instances = get_instance_ids_by_tags(tags)
    print('Instance IDs with specified tags: ', instances)
    target_instances = []

    for instance in instances:
        if not check_root_volume_created_within_last_24_hours(instance):
            print(f'The root volume associated with {instance} was not created within the last 24 hours.')
            print(f'Stopping the instance...')
            target_instances.append(instance)

        else:
            print(f'The root volume associated with {instance} was created within the last 24 hours.')
            print(f'Skipping...')

    stop_instances(target_instances)
    print('Stopped instance IDs: ', target_instances)
