import boto3
import pprint
from datetime import datetime, timezone, tzinfo


def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


EC2_AUTOSCALING_GROUP_MAX_TIME=300
# Create Auto Scaling client
client = boto3.client('autoscaling')

# Get information about all instances in an Auto Scaling group named my-auto-scaling-group.
response = client.describe_auto_scaling_groups()
current_time = datetime.now(timezone.utc)


for group in response['AutoScalingGroups']:
#   created_time = utc_to_local(datetime.strptime(group["CreatedTime"], '%Y-%m-%dT%H:%M:%S'))
  created_time = group["CreatedTime"]
  time_diff = current_time - created_time
  runtime = time_diff.total_seconds()
  print("Auto Scaling Group: ", group['AutoScalingGroupName'], " Created time:", created_time, " runtime:", runtime)
  print("Capacity:", group["MinSize"], "/", group["DesiredCapacity"], "/", group["MaxSize"])
  print("Total instances:", len(group['Instances']))
  for instance in group['Instances']:
      print("Instance ID: ", instance['InstanceId'])
      print("Health Status: ", instance['HealthStatus'])
      print("Lifecycle State: ", instance['LifecycleState'])

  if runtime> EC2_AUTOSCALING_GROUP_MAX_TIME:
    print(group['AutoScalingGroupName'],": deleting ...")
    #  response = client.update_auto_scaling_group(AutoScalingGroupName=group['AutoScalingGroupName'], MinSize=0, DesiredCapacity=0)  
    client.delete_auto_scaling_group(AutoScalingGroupName=group['AutoScalingGroupName'],ForceDelete=True)
