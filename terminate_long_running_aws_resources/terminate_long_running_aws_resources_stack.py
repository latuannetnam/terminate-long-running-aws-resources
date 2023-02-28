import os
from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as _lamda,
    aws_iam as iam,
    aws_sns as sns,
    aws_sns_subscriptions as sub_subscriptions,
    aws_events as events,
    BundlingOptions
)
from aws_solutions_constructs.aws_eventbridge_lambda import EventbridgeToLambda, EventbridgeToLambdaProps
from dotenv import load_dotenv
from constructs import Construct


class TerminateLongRunningAwsResourcesStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # Load environtment variables
        load_dotenv()

        # Create SNS Topic
        my_email = os.getenv("MY_EMAIL")
        my_topic = sns.Topic(self, "TerminateLongRunningAWSResourceTopic")
        my_topic.add_subscription(
            sub_subscriptions.EmailSubscription(my_email))

        # schedule=events.Schedule.expression("0/15 * * * ? *")
        # schedule=events.Schedule.cron(minute="0/15")
        # Terminate long running EC2 instances
        self.terminate_long_running_ec2(my_topic)

        # -----------------------------------------------------------------------
        # Create Lambda function: release unused Elastic IP Addresses
        self.release_unused_elastic_ip(my_topic)

    def terminate_long_running_ec2(self, my_topic):
        # Create Lamda function with asyncio
        # my_lambda = _lamda.Function(
        #     self, "TerminateLongRunningAwsResourcesFunction",
        #     runtime=_lamda.Runtime.PYTHON_3_9,
        #     code=_lamda.Code.from_asset(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../lamda_functions"),  bundling=BundlingOptions(
        #         image=_lamda.Runtime.PYTHON_3_9.bundling_image,
        #         command=["bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -fr ./ /asset-output"
        #                  ]
        #     )),
        #     handler="handler_terminate_long_running_aws_resources.lambda_handler",
        #     timeout=Duration.seconds(90),
        #     environment={
        #         'MAX_RUNTIME': os.getenv("MAX_RUNTIME", '3600'),
        #         'SNS_TOPIC': my_topic.topic_arn
        #     }
        # )

        # Create Lamda function with sync
        # Terminate long running EC2 instances
        my_lambda = _lamda.Function(
            self, "TerminateLongRunningAwsResourcesFunction",
            runtime=_lamda.Runtime.PYTHON_3_9,
            code=_lamda.Code.from_asset("lamda_functions"),
            handler="handler_terminate_long_running_aws_resources_sync.lambda_handler",
            timeout=Duration.seconds(90),
            environment={
                'MAX_RUNTIME': os.getenv("MAX_RUNTIME", '3600'),
                'SNS_TOPIC': my_topic.topic_arn
            }
        )

        # Add policy to Lamda Execution role
        my_lambda.add_to_role_policy(iam.PolicyStatement(
            sid="AllowToListAndTerminateEC2InstancesAndOublishToSNSTopic",
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["ec2:DescribeInstances",
                     "ec2:TerminateInstances",
                     "ec2:DescribeRegions",
                     "ec2:StopInstances",
                     "sns:Publish"],
        ))

        # Create schedule event to invoke lamda
        my_cron = os.getenv("EC2_CRON", "cron(0/15 * * * ? *)")
        EventbridgeToLambda(self, 'terminate_long_running_aws_resources_cron',
                            existing_lambda_obj=my_lambda,
                            event_rule_props=events.RuleProps(
                                schedule=events.Schedule.expression(my_cron)
                            ))

    def release_unused_elastic_ip(self, my_topic):
        my_lambda = _lamda.Function(
            self, "ReleaseUnusedElasticIPAddresses",
            runtime=_lamda.Runtime.PYTHON_3_9,
            code=_lamda.Code.from_asset("lamda_functions"),
            handler="handler_release_unused_elastic_ip.lambda_handler",
            timeout=Duration.seconds(90),
            environment={
                'ELASTIC_IP_MAX_TIME': os.getenv("ELASTIC_IP_MAX_TIME", '900'),
                'SNS_TOPIC': my_topic.topic_arn
            }
        )

        # Add policy to Lamda Execution role
        my_lambda.add_to_role_policy(iam.PolicyStatement(
            sid="AllowToListAndReleaseUnusedElasticIPAndPublishToSNSTopic",
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["ec2:CreateTags",
                     "ec2:DeleteTags",
                     "ec2:DescribeTags",
                     "ec2:DescribeAddresses",
                     "ec2:ReleaseAddress",
                     "ec2:DescribeRegions",
                     "sns:Publish"],
        ))

        # Create schedule event to invoke lamda
        my_cron = os.getenv("ELASTIC_IP_CRON", "cron(0/5 * * * ? *)")
        EventbridgeToLambda(self, 'release_unused_elastic_ip_cron',
                            existing_lambda_obj=my_lambda,
                            event_rule_props=events.RuleProps(
                                schedule=events.Schedule.expression(my_cron)
                            ))
