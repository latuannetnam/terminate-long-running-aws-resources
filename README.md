# terminate-long-running-aws-resources
Scan and terminate long running AWS resources (EC2, RDS etc.)

## Setup
The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

## Preparation
- create .env file
```
MY_EMAIL=you_email@domain.com
REGION=ap-southeast-1,us-east-1
ELASTIC_IP_MAX_TIME=900
NAT_GATEWAY_MAX_TIME=900
TRANSIT_GATEWAY_MAX_TIME=900
CLIENT_VPN_ENDPOINT_MAX_TIME=900
VPN_CONNECTION_MAX_TIME=900
EC2_AUTOSCALING_GROUP_MAX_TIME=900
ELASTIC_LOAD_BALANCER_MAX_TIME=7200
CRON=cron(0/15 * * * ? *)
```

- create .env.profile_id for non-default profile
## Test Lambda function locally

```
$ cdk synth --no-staging
```

```
$ sam local invoke TerminateLongRunningAwsResourcesFunction --no-event -t ./cdk.out/TerminateLongRunningAwsResourcesStack.template.json
```

## Deloyment
- cdk synth -c profile=profile_id --profile profile_id
- cdk diff -c profile=profile_id --profile profile_id
- cdk deploy -c profile=profile_id --profile profile_id