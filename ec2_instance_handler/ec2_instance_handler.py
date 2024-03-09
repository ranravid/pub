import boto3
# import json
import os
# import requests
from datetime import datetime, timedelta, timezone

os.environ["AWS_SHARED_CREDENTIALS_FILE"] = '~/.aws/credentials'
os.environ["AWS_DEFAULT_PROFILE"] = 'ec2_lifecycle'


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


def get_instance_ids_by_tags(tags_dict: dict) -> list:
    """Get a list of instance ids by specific dictionary of tags."""
    ec2_client = boto3.client('ec2')
    filters = [{'Name': f'tag:{tag_key}', 'Values': [tag_value]} for tag_key, tag_value in tags_dict.items()]
    response = ec2_client.describe_instances(Filters=filters)
    instance_ids = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
    return instance_ids


# def send_slack_notification(instance_ids, channel, webhook_url):
#     message = f"The following EC2 instances need attention: {', '.join(instance_ids)}"
#
#     payload = {
#         "channel": channel,
#         "text": message
#     }
#
#     headers = {
#         'Content-Type': 'application/json'
#     }
#
#     try:
#         response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
#         if response.status_code == 200:
#             print("Slack notification sent successfully.")
#         else:
#             print(f"Failed to send Slack notification. Status code: {response.status_code}")
#     except Exception as e:
#         print("Failed to send Slack notification:", str(e))


# Main
if __name__ == '__main__':
    tags = {
        'env': 'dev',
        'lifecycle': 'temporary'
    }

    instances = get_instance_ids_by_tags(tags)
    print('Instance IDs with specified tags: ', instances)
    # channel = 'your_slack_channel'
    # webhook_url = 'your_slack_webhook_url'
    target_instances = []

    for instance in instances:
        if not check_root_volume_created_within_last_24_hours(instance):
            print(f'The root volume associated with {instance} was not created within the last 24 hours.')
            print(f'Stopping the instance...')
            target_instances.append(instance)
            
        else:
            print(f'The root volume associated with {instance} was created within the last 24 hours.')

    stop_instances(target_instances)
    print('Stopped instance IDs: ', target_instances)
    # send_slack_notification(target_instances, channel, webhook_url)
