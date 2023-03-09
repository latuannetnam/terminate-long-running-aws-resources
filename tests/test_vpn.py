import boto3
import pprint
from datetime import datetime, timezone, tzinfo

# Create ec2 client
ec2_client = boto3.client('ec2')
TAG_KEY = "CREATION_TIME"
# Describe available vpn connections
response = ec2_client.describe_vpn_connections()

# Print vpn connection ids
current_time = datetime.now(timezone.utc)
for vpn_connection in response['VpnConnections']:
    vpn_connection_id= vpn_connection['VpnConnectionId']
    pprint.pprint(vpn_connection)
    last_time = None
    if 'Tags' in vpn_connection:
        for tag in vpn_connection['Tags']:
            # print(tag)
            if tag['Key'] == TAG_KEY:
                last_time = datetime.fromisoformat(tag['Value'])
                break
    if last_time is None:
        tag = {'Key': TAG_KEY, 'Value': current_time.isoformat()}
        ec2_client.create_tags(Resources=[vpn_connection_id], Tags=[tag])
    else:
        delta_time = (current_time - last_time).total_seconds()
        print("Elapsed time:", current_time, last_time, delta_time)
        if delta_time >= 100:
            print("Delete VPN connection")
            ec2_client.delete_vpn_connection(VpnConnectionId=vpn_connection_id)