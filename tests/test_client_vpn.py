import boto3
from botocore.config import Config
import os
import json
from datetime import datetime, timezone, tzinfo
from botocore.exceptions import ClientError
from enum import Enum, auto
import pprint

my_config = Config(region_name='ap-southeast-1')
client = boto3.client('ec2', config=my_config)
response = client.describe_client_vpn_endpoints()
pprint.pprint(response)

def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

current_time = datetime.now(timezone.utc)
# current_time = datetime.now()

for gateway in response['ClientVpnEndpoints']:
        gateway_id = gateway['ClientVpnEndpointId']
        creation_time  = utc_to_local(datetime.strptime(gateway['CreationTime'], '%Y-%m-%dT%H:%M:%S'))
        print(current_time, creation_time)
        time_diff = current_time - creation_time
        runtime = time_diff.total_seconds()
        print("Client VPN Endpoint:", gateway_id, " State:", gateway['Status']['Code'], " Created:", creation_time, " runtime:", runtime)