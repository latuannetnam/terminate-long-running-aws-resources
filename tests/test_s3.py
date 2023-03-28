import boto3
from botocore.exceptions import ClientError
# List all s3 buckets and check if bucket is public
s3 = boto3.client('s3')
reponse = s3.list_buckets()
for bucket in reponse['Buckets']:
    print(bucket['Name'], bucket['CreationDate'])
    try:
        acl = s3.get_public_access_block(Bucket=bucket['Name'])
        public_access = False
        # print(acl['PublicAccessBlockConfiguration'])
        for key in acl['PublicAccessBlockConfiguration']:
            if acl['PublicAccessBlockConfiguration'][key] == False:
                print(key, ":", acl['PublicAccessBlockConfiguration'][key])
                public_access = True
        if public_access:
            print("Disable public access")
            try:
                s3.put_public_access_block(Bucket=bucket['Name'], PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                },)
            except ClientError as e:
                print(e)

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchPublicAccessBlockConfiguration':
            acl = None
