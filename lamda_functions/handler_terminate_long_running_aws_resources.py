import aioboto3
from botocore.config import Config
import os
import json
from datetime import datetime, timezone, tzinfo
import asyncio

max_runtime = int(os.environ.get('MAX_RUNTIME', '3600'))
sns_topicARN = os.environ.get('SNS_TOPIC','')
sns_message={}
current_time = datetime.now(timezone.utc)

async def available_regions(service):
    regions = []
    # client = boto3.client(service)
    session = aioboto3.Session()
    async with session.client(service) as client:
        response = await client.describe_regions()
        for item in response["Regions"]:
            regions.append(item["RegionName"])

    return regions

async def check_long_running_instances(region):
    print("Check Region:", region)
    my_config = Config(region_name=region)
    session = aioboto3.Session()
    async with session.client('ec2', config=my_config) as client:
        response = await client.describe_instances(Filters=[{
                    'Name': 'instance-state-name',
                    'Values': ['running']
                }])
        # print(response)
        if len(response["Reservations"]) >0:
            print("Check Region:", region)
        
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:    
                # pprint(instance)
                launch_time = instance["LaunchTime"]
                time_diff = current_time - launch_time
                runtime = time_diff.total_seconds()
                state = instance["State"]["Name"]
                can_terminate = True
                if 'Tags' in instance:
                    for tag in instance["Tags"]:
                        if tag["Key"] == "TerminalProtection" and (tag["Value"] == "Yes" or tag["Value"] == "On" or tag["Value"] == "1"):
                            can_terminate = False
                            break

                print("state:", state, "run time:", runtime,"/", max_runtime, " can_terminate:", can_terminate)
                instance_id = instance["InstanceId"]
                regional_instance_id = region + "-" + instance_id
                if state=="running" and runtime>= max_runtime and can_terminate:
                    print("Terminating instance:", regional_instance_id)
                    try:
                        await client.terminate_instances(InstanceIds=[instance_id])
                        sns_message[regional_instance_id] = "Terminated"
                    except Exception  as e:
                        print("Can not terminate instance:", instance["InstanceId"], "reason:", e)
                        sns_message[regional_instance_id] = "Try to Terminate but failed with reason:" + str(e)
                else:
                    sns_message[regional_instance_id] = "Not Terminated"
    print("Check Region:", region, " Done!")

async def async_handler(event, context):
    regions = await available_regions('ec2')
    tasks = []
    for region in regions:
        tasks.append(asyncio.create_task(check_long_running_instances(region)))
    await asyncio.gather(*tasks)
    if sns_topicARN != '':
        async with aioboto3.client('sns') as client:
            response = await client.publish(
                TopicArn=sns_topicARN,
                Message=json.dumps(sns_message),
                Subject='Long Running Instances Report'
            )
    return {
        'statusCode': 200,
        'body': json.dumps(sns_message)
    }


def lambda_handler(event, context):
    print("Begin to scan resources")
    result = asyncio.run(async_handler(None, None))    
    print("Done!")
    return result


if __name__ == "__main__":
    print("Run test lamda function locally")
    print(lambda_handler(None, None))    