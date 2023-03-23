import os
from dotenv import load_dotenv
import boto3

load_dotenv()


def get_available_regions():
    session = boto3.session.Session()
    return session.get_available_regions('s3')


def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i+1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]


session = boto3.session.Session()
region_name = session.region_name
print("current region:", region_name)
region_str = os.getenv('REGION')
regions = ()
if region_str is not None:
    regions = region_str.split(',')
print("Regions:", regions)
