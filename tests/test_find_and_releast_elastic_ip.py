import boto3
import pprint
import time
from datetime import datetime, timezone, tzinfo
from botocore.exceptions import ClientError
TAG_KEY = "Epoch"
ELASTIC_IP_MAX_TIME = 10
ec2 = boto3.client('ec2')
response = ec2.describe_addresses()
# current_time = datetime.now(timezone.utc)
current_time = time.time()
for address in response['Addresses']:
    pprint.pprint(address)
    allocation_id = address['AllocationId']
    if 'AssociationId' not in address:
        print("Address: ", allocation_id, "-",
              address["PublicIp"], "is not associated with any resources")
        last_epoch = 0

        current_epoch = int(current_time)
        if 'Tags' in address:
            for tag in address['Tags']:
                # print(tag)
                if tag['Key'] == TAG_KEY:
                    last_epoch = int(tag['Value'])

        if last_epoch == 0:
            #   Create tag
            ec2.create_tags(Resources=[allocation_id], Tags=[
                            {'Key': TAG_KEY, 'Value': str(current_epoch)}])
        else:
            delta_time = current_epoch - last_epoch
            print("Elapsed time:", current_epoch, last_epoch, delta_time)
            if delta_time >= ELASTIC_IP_MAX_TIME:
                try:
                    print("Release Elastic IP:", allocation_id,
                          "-", address["PublicIp"])
                    ec2.release_address(AllocationId=allocation_id)
                except ClientError as e:
                    print(e)

    else:
        # Delete tags
        print("Delete tag:", TAG_KEY, " from ",
              allocation_id, "-", address["PublicIp"])
        ec2.delete_tags(Resources=[allocation_id], Tags=[{'Key': TAG_KEY, }])

        # ec2.create_tags(Resources=[allocation_id], Tags=[{'Key': 'Name', 'Value': 'MyEIP'}])
        # print(f"Releasing {address['AllocationId']}")
        # ec2.release_address(AllocationId=address['AllocationId'])
