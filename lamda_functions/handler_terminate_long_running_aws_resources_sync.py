import boto3
from botocore.config import Config
import os
import json
from datetime import datetime, timezone, tzinfo
from botocore.exceptions import ClientError
from enum import Enum, auto
import pprint

# Constants
TAG_KEY = "Epoch"
REGION = os.getenv('REGION')
MAX_RUNTIME = int(os.environ.get('MAX_RUNTIME', '3600'))
ELASTIC_IP_MAX_TIME = int(os.environ.get('ELASTIC_IP_MAX_TIME', '900'))
NAT_GATEWAY_MAX_TIME = int(os.environ.get('NAT_GATEWAY_MAX_TIME', '900'))
TRANSIT_GATEWAY_MAX_TIME = int(
    os.environ.get('TRANSIT_GATEWAY_MAX_TIME', '900'))
CLIENT_VPN_ENDPOINT_MAX_TIME = int(
    os.environ.get('CLIENT_VPN_ENDPOINT_MAX_TIME', '900'))
VPN_CONNECTION_MAX_TIME = int(os.environ.get('VPN_CONNECTION_MAX_TIME', '900'))
EC2_AUTOSCALING_GROUP_MAX_TIME = int(
    os.environ.get('EC2_AUTOSCALING_GROUP_MAX_TIME', '900'))
ELASTIC_LOAD_BALANCER_MAX_TIME = int(
    os.environ.get('ELASTIC_LOAD_BALANCER_MAX_TIME', '900'))
RDS_MAX_TIME = int(os.environ.get('RDS_MAX_TIME', '900'))

S3_PUBLIC_ACCESS_MAX_TIME = int(
    os.environ.get('S3_PUBLIC_ACCESS_MAX_TIME', '900'))

sns_topicARN = os.environ.get('SNS_TOPIC')


def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


class ServiceTypes(str, Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    EC2 = auto()
    ELASTIC_IP = auto()
    NAT_GATEWAY = auto()
    TRANSIT_GATEWAY = auto()
    CLIENT_VPN_ENDPOINT = auto()
    VPN_CONNECTION = auto()
    EC2_AUTOSCALING_GROUP = auto()
    ELASTIC_LOAD_BALANCER = auto()
    ELB_TARGET_GROUP = "Manual delete target group"
    RDS_INSTANCE = auto()
    RDS_CLUSTER = auto()
    S3_PUBLIC_ACCESS = auto()


class TerminateLongRunningResource:
    def __init__(self) -> None:
        self.sns_message = {}
        for service in ServiceTypes:
            self.sns_message[service] = {}
        # pprint.pprint(self.sns_message)

    def available_regions(self, service):
        regions = []
        client = boto3.client(service)
        response = client.describe_regions()

        for item in response["Regions"]:
            regions.append(item["RegionName"])

        return regions

    def get_env_regions(self):
        regions = []
        if REGION is not None:
            if REGION != 'ALL':
                regions = REGION.split(',')
            else:
                regions = self.available_regions("ec2")
        else:
            session = boto3.session.Session()
            region_name = session.region_name
            # region_name = "us-east-1"
            regions.append(region_name)
        print("Regions:", regions)
        return regions

    def check_long_running_elastic_load_balancers(self, region):
        current_time = datetime.now(timezone.utc)
        my_config = Config(region_name=region)
        client = boto3.client('elbv2', config=my_config)
        response = client.describe_load_balancers()
        for elb in response['LoadBalancers']:
            created_time = elb["CreatedTime"]
            time_diff = current_time - created_time
            runtime = time_diff.total_seconds()
            elb_group_id = elb['LoadBalancerArn']
            region_id = region + "-" + elb_group_id
            print("ELB: ", region_id, " Created time:", created_time,
                  " runtime:", runtime, "/", ELASTIC_LOAD_BALANCER_MAX_TIME)

            if runtime >= ELASTIC_LOAD_BALANCER_MAX_TIME:
                # List all target group of ELB
                target_groups = []
                target_groups_response = client.describe_target_groups(
                    LoadBalancerArn=elb_group_id)
                for target_group in target_groups_response['TargetGroups']:
                    target_group_id = target_group['TargetGroupName'] + \
                        ":" + target_group['TargetGroupArn']
                    target_groups.append(target_group_id)

                separator = ', '
                self.sns_message[ServiceTypes.ELB_TARGET_GROUP][region_id] = separator.join(
                    target_groups)
                print("ELB:", region_id, " deleting ...")
                try:
                    client.delete_load_balancer(LoadBalancerArn=elb_group_id)
                    self.sns_message[ServiceTypes.ELASTIC_LOAD_BALANCER][region_id] = "Deleted"

                except Exception as e:
                    print("Can not delete ELB:", region_id, ". reason:", e)
                    self.sns_message[ServiceTypes.ELASTIC_LOAD_BALANCER][
                        region_id] = "Try to Terminate but failed with reason:" + str(e)

    def check_long_running_ec2_autoscaling_groups(self, region):
        current_time = datetime.now(timezone.utc)
        my_config = Config(region_name=region)
        client = boto3.client('autoscaling', config=my_config)
        response = client.describe_auto_scaling_groups()
        for group in response['AutoScalingGroups']:
            created_time = group["CreatedTime"]
            time_diff = current_time - created_time
            runtime = time_diff.total_seconds()
            autoscaling_group_id = group['AutoScalingGroupName']
            region_id = region + "-" + autoscaling_group_id
            print("Auto Scaling Group: ", region_id, " Created time:",
                  created_time, " runtime:", runtime)
            print("Capacity:", group["MinSize"], "/",
                  group["DesiredCapacity"], "/", group["MaxSize"])
            print("Total instances:", len(group['Instances']))

            if runtime >= EC2_AUTOSCALING_GROUP_MAX_TIME:
                print("AutoScaling group:", region_id, " deleting ...")
                try:
                    client.delete_auto_scaling_group(
                        AutoScalingGroupName=group['AutoScalingGroupName'], ForceDelete=True)
                    self.sns_message[ServiceTypes.EC2_AUTOSCALING_GROUP][region_id] = "Deleted"
                except Exception as e:
                    print("Can not delete autoscaling group:",
                          region_id, "reason:", e)
                    self.sns_message[ServiceTypes.EC2_AUTOSCALING_GROUP][
                        region_id] = "Try to Terminate but failed with reason:" + str(e)

    def check_long_running_instances(self, region):
        # print("Check Region:", region)
        current_time = datetime.now(timezone.utc)
        my_config = Config(region_name=region)
        client = boto3.client('ec2', config=my_config)
        response = client.describe_instances(Filters=[{
            'Name': 'instance-state-name',
                    'Values': ['running']
        }])
        # print(response)
        if len(response["Reservations"]) > 0:
            print("Check Region:", region)

        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                # pprint(instance)
                launch_time = instance["LaunchTime"]
                time_diff = current_time - launch_time
                runtime = time_diff.total_seconds()
                state = instance["State"]["Name"]
                can_terminate = True
                # if 'Tags' in instance:
                #     for tag in instance["Tags"]:
                #         if tag["Key"] == "TerminalProtection" and (tag["Value"] == "Yes" or tag["Value"] == "On" or tag["Value"] == "1"):
                #             can_terminate = False
                #             break

                instance_id = instance["InstanceId"]
                regional_instance_id = region + "-" + instance_id

                if state == "running" and runtime >= MAX_RUNTIME and can_terminate:
                    print(regional_instance_id, ": state:", state, "run time:",
                      runtime, "/", MAX_RUNTIME, " can_terminate:", can_terminate)
                    print("Terminate instance:", regional_instance_id)
                    try:
                        client.terminate_instances(InstanceIds=[instance_id])
                        self.sns_message[ServiceTypes.EC2][regional_instance_id] = "Terminated"
                    except Exception as e:
                        print("Can not terminate instance:",
                              instance["InstanceId"], "reason:", e)
                        self.sns_message[ServiceTypes.EC2][regional_instance_id] = "Try to Terminate but failed with reason:" + str(
                            e)

    def find_and_release_unused_elastic_ip(self, region):
        current_time = datetime.now(timezone.utc)
        my_config = Config(region_name=region)
        ec2 = boto3.client('ec2', config=my_config)
        response = ec2.describe_addresses()
        for address in response['Addresses']:
            allocation_id = address['AllocationId']
            regional_id = region + "-" + \
                allocation_id + "-" + address["PublicIp"]
            if 'AssociationId' not in address:
                print("Address: ", regional_id, "-",
                      address["PublicIp"], "is not associated with any resources")
                last_time = None

                if 'Tags' in address:
                    for tag in address['Tags']:
                        # print(tag)
                        if tag['Key'] == TAG_KEY:
                            last_time = datetime.fromisoformat(tag['Value'])

                if last_time is None:
                    #   Create tag
                    tag = {'Key': TAG_KEY, 'Value': current_time.isoformat()}
                    ec2.create_tags(Resources=[allocation_id], Tags=[tag])
                    print("Address: ", allocation_id, "-",
                          address["PublicIp"], "is Tagged with:", tag)
                else:
                    delta_time = (current_time - last_time).total_seconds()
                    print(regional_id, "Elapsed time:",
                          current_time, last_time, delta_time)
                    if delta_time >= ELASTIC_IP_MAX_TIME:

                        print("Release Elastic IP:", regional_id,
                              "-", address["PublicIp"])
                        try:
                            ec2.release_address(AllocationId=allocation_id)
                            self.sns_message[ServiceTypes.ELASTIC_IP][regional_id] = "Released"
                        except ClientError as e:
                            print(e)
                            self.sns_message[ServiceTypes.ELASTIC_IP][regional_id] = "Try to Release but failed with reason:" + str(
                                e)

            else:
                if 'Tags' in address:
                    # Delete tags
                    print("Delete tag:", TAG_KEY, " from ",
                          allocation_id, "-", address["PublicIp"])
                    ec2.delete_tags(Resources=[allocation_id], Tags=[
                                    {'Key': TAG_KEY, }])

    def check_long_running_nat_gateways(self, region):
        # print("Check Region:", region)
        # print(region, self.sns_message)
        current_time = datetime.now(timezone.utc)
        my_config = Config(region_name=region)
        client = boto3.client('ec2', config=my_config)
        response = client.describe_nat_gateways()
        for nat_gateway in response['NatGateways']:
            nat_gateway_id = region + "-" + nat_gateway['NatGatewayId']
            time_diff = current_time - nat_gateway['CreateTime']
            runtime = time_diff.total_seconds()
            print("Nat gateway:", nat_gateway_id, " State:",
                  nat_gateway['State'], " Created:", nat_gateway['CreateTime'], " runtime:", runtime)
            if nat_gateway['State'] == 'available':
                if runtime >= NAT_GATEWAY_MAX_TIME:
                    print("Delete long running NAT Gateway:", nat_gateway_id,
                          " runtime:", runtime, "/", NAT_GATEWAY_MAX_TIME)
                    try:
                        client.delete_nat_gateway(
                            NatGatewayId=nat_gateway['NatGatewayId'])
                        self.sns_message[ServiceTypes.NAT_GATEWAY][nat_gateway_id] = "Deleted"
                    except ClientError as e:
                        print(e)
                        self.sns_message[ServiceTypes.NAT_GATEWAY][nat_gateway_id] = "Try to delete but failed with reason:" + str(
                            e)

    def check_long_running_transit_gateway(self, region):
        current_time = datetime.now(timezone.utc)
        my_config = Config(region_name=region)
        client = boto3.client('ec2', config=my_config)
        response = client.describe_transit_gateways()
        for gateway in response['TransitGateways']:
            gateway_id = region + "-" + gateway['TransitGatewayId']
            time_diff = current_time - gateway['CreationTime']
            runtime = time_diff.total_seconds()
            print("Transit gateway:", gateway_id, " State:",
                  gateway['State'], " Created:", gateway['CreationTime'], " runtime:", runtime)
            if gateway['State'] == 'available':
                if runtime >= TRANSIT_GATEWAY_MAX_TIME:
                    print("List and delete all gateway attachments:")
                    res = client.describe_transit_gateway_attachments(Filters=[
                        {
                            'Name': 'transit-gateway-id',
                            'Values': [gateway['TransitGatewayId']]
                        }
                    ])
                    # print(res)
                    for gateway_attachment in res['TransitGatewayAttachments']:
                        print("Delete Transit gateway attachment:",
                              gateway_attachment['TransitGatewayAttachmentId'])
                        client.delete_transit_gateway_vpc_attachment(
                            TransitGatewayAttachmentId=gateway_attachment['TransitGatewayAttachmentId'])

                    print("Delete long running Transit Gateway:", gateway_id,
                          " runtime:", runtime, "/", TRANSIT_GATEWAY_MAX_TIME)
                    try:
                        client.delete_transit_gateway(
                            TransitGatewayId=gateway['TransitGatewayId'])
                        self.sns_message[ServiceTypes.TRANSIT_GATEWAY][gateway_id] = "Deleted"
                    except ClientError as e:
                        print(e)
                        self.sns_message[ServiceTypes.TRANSIT_GATEWAY][gateway_id] = "Try to delete but failed with reason:" + str(
                            e)

    def check_long_running_client_vpn_endpoints(self, region):
        # print("Region:", region)
        current_time = datetime.now(timezone.utc)
        my_config = Config(region_name=region)
        client = boto3.client('ec2', config=my_config)
        try:
            response = client.describe_client_vpn_endpoints()
        except ClientError as e:
            print("Can not list client vpn endpoints for region:",
                  region, "  .reason:" + str(e))
            return

        for gateway in response['ClientVpnEndpoints']:
            gateway_id = region + "-" + gateway['ClientVpnEndpointId']
            creation_time = utc_to_local(datetime.strptime(
                gateway['CreationTime'], '%Y-%m-%dT%H:%M:%S'))
            time_diff = current_time - creation_time
            runtime = time_diff.total_seconds()
            print("Client VPN Endpoint:", gateway_id, " State:",
                  gateway['Status']['Code'], " Created:", creation_time, " runtime:", runtime)
            if gateway['Status']['Code'] == 'available' or gateway['Status']['Code'] == 'pending-associate':
                if runtime >= CLIENT_VPN_ENDPOINT_MAX_TIME:
                    print("List and delete all associated  target networks:")
                    res = client.describe_client_vpn_target_networks(
                        ClientVpnEndpointId=gateway['ClientVpnEndpointId'])
                    for target in res['ClientVpnTargetNetworks']:
                        print("Disassocating target:", target['AssociationId'])
                        client.disassociate_client_vpn_target_network(
                            ClientVpnEndpointId=gateway['ClientVpnEndpointId'], AssociationId=target['AssociationId'])

                    # Delete client vpn endpoint
                    print("Delete long running Client VPN Endpoints:", gateway_id,
                          " runtime:", runtime, "/", CLIENT_VPN_ENDPOINT_MAX_TIME)
                    try:
                        client.delete_client_vpn_endpoint(
                            ClientVpnEndpointId=gateway['ClientVpnEndpointId'])
                        self.sns_message[ServiceTypes.CLIENT_VPN_ENDPOINT][gateway_id] = "Deleted"
                    except ClientError as e:
                        print(e)
                        self.sns_message[ServiceTypes.CLIENT_VPN_ENDPOINT][
                            gateway_id] = "Try to delete but failed with reason:" + str(e)

    def check_long_running_vpn_connections(self, region):
        # print("Region:", region)
        current_time = datetime.now(timezone.utc)
        my_config = Config(region_name=region)
        client = boto3.client('ec2', config=my_config)
        try:
            response = client.describe_vpn_connections()
        except ClientError as e:
            print("Can not list vpn connections for region:",
                  region, "  .reason:" + str(e))
            return

        for vpn_connection in response['VpnConnections']:
            vpn_connection_id = vpn_connection['VpnConnectionId']
            vpn_connection_region_id = region + "-" + vpn_connection_id
            last_time = None
            if 'Tags' in vpn_connection:
                for tag in vpn_connection['Tags']:
                    # print(tag)
                    if tag['Key'] == TAG_KEY:
                        last_time = datetime.fromisoformat(tag['Value'])
                        break
            if last_time is None:
                if vpn_connection['State'] != 'deleting' and vpn_connection['State'] != 'deleted':
                    tag = {'Key': TAG_KEY, 'Value': current_time.isoformat()}
                    client.create_tags(
                        Resources=[vpn_connection_id], Tags=[tag])
                    print(vpn_connection_region_id, "State:",
                          vpn_connection['State'], ". Creation time:", current_time)
            else:
                delta_time = (current_time - last_time).total_seconds()
                print(vpn_connection_region_id, "Elapsed time:",
                      current_time, last_time, delta_time)
                if delta_time >= VPN_CONNECTION_MAX_TIME:
                    print("Delete VPN connection:", vpn_connection_region_id,
                          ". Runtime:", delta_time, "/", VPN_CONNECTION_MAX_TIME)
                    try:
                        client.delete_vpn_connection(
                            VpnConnectionId=vpn_connection_id)
                        self.sns_message[ServiceTypes.VPN_CONNECTION][
                            vpn_connection_region_id] = "Deleted"
                    except ClientError as e:
                        print(e)
                        self.sns_message[ServiceTypes.VPN_CONNECTION][
                            vpn_connection_region_id] = "Try to delete but failed with reason:" + str(e)

    # Delete db instance
    def delete_db_instance(self, client, db_instance_region_id, db_instance_id):
        print("Delete long running RDS instances:",
                          db_instance_region_id)
        try:
            client.delete_db_instance(
                DBInstanceIdentifier=db_instance_id, SkipFinalSnapshot=True)
            self.sns_message[ServiceTypes.RDS_INSTANCE][db_instance_region_id] = "Deleted"
        except ClientError as e:
            print(e)
            self.sns_message[ServiceTypes.RDS_INSTANCE][
                db_instance_region_id] = "Try to delete but failed with reason:" + str(e)

    # List and delete long runinng RDS instances
    def check_long_running_rds_instances(self, region):
        current_time = datetime.now(timezone.utc)
        my_config = Config(region_name=region)
        client = boto3.client('rds', config=my_config)
        response = client.describe_db_instances()
        for db_instance in response['DBInstances']:
            db_instance_id = db_instance['DBInstanceIdentifier']
            db_instance_region_id = region + "-" + db_instance_id
            creation_time = db_instance['InstanceCreateTime']
            # print("RDS Instance:", db_instance_region_id, runtime, "/", RDS_MAX_TIME)
            if db_instance['DBInstanceStatus'] != 'available':
                time_diff = current_time - creation_time
                runtime = time_diff.total_seconds()
                if runtime >= RDS_MAX_TIME:
                    print("RDS Instance:", db_instance_region_id, runtime, "/", RDS_MAX_TIME)
                    self.delete_db_instance(client, db_instance_region_id, db_instance_id)
                        
    
    # List and delete long running RDS clusters
    def check_long_running_rds_clusters(self, region):
        current_time = datetime.now(timezone.utc)
        my_config = Config(region_name=region)
        client = boto3.client('rds', config=my_config)
        response = client.describe_db_clusters()
        for cluster in response['DBClusters']:
            cluster_id = cluster['DBClusterIdentifier']
            cluster_region_id = region + "-" + cluster_id
            creation_time = cluster['ClusterCreateTime']
            if cluster['Status'] != 'deleting' and cluster['Status'] != 'deleted':
                time_diff = current_time - creation_time
                runtime = time_diff.total_seconds()
                if runtime >= RDS_MAX_TIME:
                    print("RDS cluster:", cluster_region_id, runtime, "/", RDS_MAX_TIME)
                    print("Delete long running RDS instances:")
                    db_instances = client.describe_db_instances(Filters=[
                                                                {
                                                                    'Name': 'db-cluster-id',
                                                                    'Values': [
                                                                        cluster_id,
                                                                    ]
                                                                },
                                                            ],)
                    for db_instance in db_instances['DBInstances']:
                        db_instance_id = db_instance['DBInstanceIdentifier']
                        db_instance_region_id = region + "-" + db_instance_id
                        if db_instance['DBInstanceStatus'] != 'deleting' and db_instance['DBInstanceStatus'] != 'deleted':
                            print("RDS Instance:", db_instance_region_id, runtime, "/", RDS_MAX_TIME)
                            self.delete_db_instance(client, db_instance_region_id, db_instance_id)
                    
                    # Delete RDS Cluster                          
                    try:
                        client.delete_db_cluster(DBClusterIdentifier=cluster_id, SkipFinalSnapshot=True)
                        self.sns_message[ServiceTypes.RDS_CLUSTER][cluster_region_id] = "Deleted"
                    except ClientError as e:
                        print(e)
                        self.sns_message[ServiceTypes.RDS_CLUSTER][
                            cluster_region_id] = "Try to delete but failed with reason:" + str(e)



    def s3_block_public_access(self, client, bucket_name):
        try:
            client.put_public_access_block(Bucket=bucket_name,
                                            PublicAccessBlockConfiguration={
                                                'BlockPublicAcls': True,
                                                'IgnorePublicAcls': True,
                                                'BlockPublicPolicy': True,
                                                'RestrictPublicBuckets': True
                                            },)
            self.sns_message[ServiceTypes.S3_PUBLIC_ACCESS][bucket_name] = "Disabled"
        except ClientError as e:
            print(e)
            self.sns_message[ServiceTypes.S3_PUBLIC_ACCESS][bucket_name] = "Try to disable but failed with reason:" + str(e)

    # List all S3 buckets and disable Public Access
    def check_public_access_s3_buckets(self):
        current_time = datetime.now(timezone.utc)
        client = boto3.client('s3')
        response = client.list_buckets()
        for bucket in response['Buckets']:
            bucket_name = bucket['Name']
            bucket_region_id = bucket_name
            creation_time = bucket['CreationDate']
            time_diff = current_time - creation_time
            runtime = time_diff.total_seconds()
            # print("Bucket:", bucket_region_id, runtime)
            if runtime >= S3_PUBLIC_ACCESS_MAX_TIME:
                try:
                    acl = client.get_public_access_block(Bucket=bucket_name)
                    public_access = False
                    # print(acl['PublicAccessBlockConfiguration'])
                    for key in acl['PublicAccessBlockConfiguration']:
                        if acl['PublicAccessBlockConfiguration'][key] == False:
                            print(
                                key, ":", acl['PublicAccessBlockConfiguration'][key])
                            public_access = True
                    
                    if public_access:
                        print("Bucket:", bucket_region_id, " runtime:", runtime, "/", S3_PUBLIC_ACCESS_MAX_TIME,  ":Public access is enabled. Disabling ...")
                        self.s3_block_public_access(client, bucket_name)

                except ClientError as e:
                    # print(e)
                    if e.response['Error']['Code'] == 'NoSuchPublicAccessBlockConfiguration':
                        acl = None
                        print("Bucket:", bucket_region_id, " runtime:", runtime, "/", S3_PUBLIC_ACCESS_MAX_TIME,  ":Public access is enabled. Disabling ...")
                        self.s3_block_public_access(client, bucket_name)


    def run_handler(self):
        # regions = self.available_regions("ec2")
        regions = self.get_env_regions()
        for region in regions:
            self.check_long_running_elastic_load_balancers(region)
            self.check_long_running_ec2_autoscaling_groups(region)
            self.check_long_running_instances(region)
            self.find_and_release_unused_elastic_ip(region)
            self.check_long_running_nat_gateways(region)
            self.check_long_running_transit_gateway(region)
            self.check_long_running_client_vpn_endpoints(region)
            self.check_long_running_vpn_connections(region)
            self.check_long_running_rds_clusters(region)
            self.check_long_running_rds_instances(region)

        # Check Global services
        self.check_public_access_s3_buckets()

        can_send_message = False
        for service in ServiceTypes:
            if self.sns_message[service]:
                can_send_message = True
                pprint.pprint(self.sns_message)
                break

        if can_send_message and sns_topicARN:
            sns_client = boto3.client('sns', region_name='ap-southeast-1')
            resp = sns_client.publish(
                TopicArn=sns_topicARN,
                Message=json.dumps(
                    {'default': json.dumps(self.sns_message, indent=4)}),
                Subject='Terminate long running resources Warning',
                MessageStructure='json'
            )


# ------------------ Lambda handler ---------------------
def lambda_handler(event, context):
    obj = TerminateLongRunningResource()
    obj.run_handler()
    return {
        'statusCode': 200,
        'body': json.dumps('ok')
    }


if __name__ == "__main__":
    print("Run test lamda function locally")
    lambda_handler(None, None)
