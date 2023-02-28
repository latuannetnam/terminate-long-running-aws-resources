import boto3
from botocore.config import Config
import os
import json
from datetime import datetime, timezone, tzinfo
from botocore.exceptions import ClientError

TAG_KEY = "Epoch"
ELASTIC_IP_MAX_TIME = int(os.environ.get('ELASTIC_IP_MAX_TIME', '900'))
sns_topicARN = os.environ.get('SNS_TOPIC','')
sns_message={}


def available_regions(service):
    regions = []
    client = boto3.client(service)
    response = client.describe_regions()

    for item in response["Regions"]:
        regions.append(item["RegionName"])

    return regions

def find_and_release_unused_elastic_ip(region):
    current_time = datetime.now(timezone.utc)
    my_config = Config(region_name=region)
    ec2 = boto3.client('ec2', config=my_config)
    response = ec2.describe_addresses()
    for address in response['Addresses']:
        allocation_id = address['AllocationId']
        if 'AssociationId' not in address:
            print("Address: ", allocation_id, "-",
                address["PublicIp"], "is not associated with any resources")
            last_time = None
            
            
            if 'Tags' in address:
                for tag in address['Tags']:
                    # print(tag)
                    if tag['Key'] == TAG_KEY:
                        last_time = datetime.fromisoformat(tag['Value'])

            if last_time is None :
                #   Create tag
                tag = {'Key': TAG_KEY, 'Value': current_time.isoformat()}
                ec2.create_tags(Resources=[allocation_id], Tags=[tag])
                print("Address: ", allocation_id, "-", address["PublicIp"], "is Tagged with:", tag)
            else:
                delta_time = (current_time - last_time).total_seconds()
                print("Elapsed time:", current_time, last_time, delta_time)
                if delta_time >= ELASTIC_IP_MAX_TIME:
                    regional_id = region + "-" + allocation_id + "-" + address["PublicIp"]
                    try:
                        print("Release Elastic IP:", allocation_id, "-", address["PublicIp"])
                        ec2.release_address(AllocationId=allocation_id)
                        sns_message[regional_id] = "Released"
                    except ClientError as e:
                        print(e)
                        sns_message[regional_id] = "Try to Release but failed with reason:" + str(e)

        else:
            if 'Tags' in address:
                # Delete tags
                print("Delete tag:", TAG_KEY," from ", allocation_id, "-", address["PublicIp"])
                ec2.delete_tags(Resources=[allocation_id], Tags=[{'Key': TAG_KEY,}])

def lambda_handler(event, context):
    sns_message={}
    regions = available_regions("ec2")
    for region in regions:
        find_and_release_unused_elastic_ip(region)
    
    if sns_message and sns_topicARN:
        sns_client = boto3.client('sns', region_name='ap-southeast-1')
        resp = sns_client.publish(
            TopicArn=sns_topicARN,
            Message=json.dumps({'default': json.dumps(sns_message, indent=4)}),
            Subject='Elastic IP Release Warning',
            MessageStructure='json'
        )
    return {
        'statusCode': 200,
        'body': json.dumps('ok')
    }


if __name__ == "__main__":
    print("Run test lamda function locally")
    lambda_handler(None, None)