import os
from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as _lamda,
    aws_iam as iam,
    aws_sns as sns,
    aws_sns_subscriptions as sub_subscriptions,
    aws_events as events,
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
        my_topic.add_subscription(sub_subscriptions.EmailSubscription(my_email))

        # Create Lamda function
        my_lambda = _lamda.Function(
            self, "TerminateLongRunningAwsResourcesFunction",
            runtime=_lamda.Runtime.PYTHON_3_9,
            code = _lamda.Code.from_asset("lamda_functions"),
            handler="handler_terminate_long_running_aws_resources.lambda_handler",
            timeout=Duration.seconds(90),
            environment= {
                'MAX_RUNTIME': os.getenv("MAX_RUNTIME", '3600'),
                'SNS_TOPIC': my_topic.topic_arn
            }
        )
        
        #Add policy to Lamda Execution role
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
        EventbridgeToLambda(self, 'terminate_long_running_aws_resources_cron',
                    existing_lambda_obj=my_lambda,
                    event_rule_props=events.RuleProps(
                        schedule=events.Schedule.cron(minute="0/15")
                    ))

        

        
