import os
import aws_cdk
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
        profile = self.node.try_get_context("profile")
        print("Load context:", profile)
        if profile:
            env_file = ".env." + profile
            print("Load env:",env_file)
            if not load_dotenv(env_file):
                print("Can not load env:", env_file)
                load_dotenv()
        else:
            load_dotenv()

        # Create SNS Topic
        my_email = os.getenv("MY_EMAIL")
        my_topic = sns.Topic(self, "TerminateLongRunningAWSResourceTopic")
        my_topic.add_subscription(
            sub_subscriptions.EmailSubscription(my_email))

        # Terminate long running EC2 instances
        self.terminate_long_running_resources(my_topic)

        aws_cdk.CfnOutput(self, "SNS Topic", value=my_topic.topic_arn)

        # -----------------------------------------------------------------------
        # Create Lambda function: release unused Elastic IP Addresses
        # self.release_unused_elastic_ip(my_topic)

    def terminate_long_running_resources(self, my_topic):
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
            timeout=Duration.seconds(int(os.environ.get('LAMBDA_MAX_RUNTIME', '360'))),
            environment={
                'MAX_RUNTIME': os.getenv("MAX_RUNTIME", '3600'),
                'ELASTIC_IP_MAX_TIME': os.getenv("ELASTIC_IP_MAX_TIME", '900'),
                'NAT_GATEWAY_MAX_TIME': os.getenv("NAT_GATEWAY_MAX_TIME", '900'),
                'TRANSIT_GATEWAY_MAX_TIME':os.environ.get('TRANSIT_GATEWAY_MAX_TIME', '900'),
                'CLIENT_VPN_ENDPOINT_MAX_TIME':os.environ.get('CLIENT_VPN_ENDPOINT_MAX_TIME', '900'),
                'VPN_CONNECTION_MAX_TIME':os.environ.get('VPN_CONNECTION_MAX_TIME', '900'),
                'EC2_AUTOSCALING_GROUP_MAX_TIME':os.environ.get('EC2_AUTOSCALING_GROUP_MAX_TIME', '900'),
                'ELASTIC_LOAD_BALANCER_MAX_TIME':os.environ.get('ELASTIC_LOAD_BALANCER_MAX_TIME', '900'),

                'SNS_TOPIC': my_topic.topic_arn
            }
        )

        # Add policy to Lamda Execution role to list and terminate EC2 instance
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

        # Add policy to Lamda Execution role to list and release Elastic IP
        my_lambda.add_to_role_policy(iam.PolicyStatement(
            sid="AllowToListAndReleaseUnusedElasticIP",
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["ec2:CreateTags",
                     "ec2:DeleteTags",
                     "ec2:DescribeTags",
                     "ec2:DescribeAddresses",
                     "ec2:ReleaseAddress",
            ]        
        ))

        # Add policy to Lamda Execution role to list and delete NAT Gateway
        my_lambda.add_to_role_policy(iam.PolicyStatement(
            sid="AllowToListAndDeleteNATGateway",
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["ec2:DescribeNatGateways",
                     "ec2:DeleteNatGateway",
            ]        
        ))

        # Add policy to Lamda Execution role to list and delete Transit Gateway
        my_lambda.add_to_role_policy(iam.PolicyStatement(
            sid="AllowToListAndDeleteTransitGateway",
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["ec2:DescribeTransitGateways",
                     "ec2:DeleteTransitGateway",
                     "ec2:DescribeTransitGatewayAttachments",
                     "ec2:DeleteTransitGatewayVpcAttachment",
            ]        
        ))

        # Add policy to Lamda Execution role to list and delete Client VPN Endpoints
        my_lambda.add_to_role_policy(iam.PolicyStatement(
            sid="AllowToListAndDeleteClientVPNEndpoints",
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["ec2:DescribeClientVpnEndpoints",
                     "ec2:DescribeClientVpnTargetNetworks",
                     "ec2:DisassociateClientVpnTargetNetwork",
                     "ec2:DeleteClientVpnEndpoint",
            ]        
        ))

        # Add policy to Lamda Execution role to list and delete VPN Connection
        my_lambda.add_to_role_policy(iam.PolicyStatement(
            sid="AllowToListAndDeleteVPNConnections",
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["ec2:DescribeVpnConnections",
                     "ec2:DeleteVpnConnection",                    
            ]        
        ))

        # Add policy to Lamda Execution role to list and delete VPN Connection
        my_lambda.add_to_role_policy(iam.PolicyStatement(
            sid="AllowToListAndDeleteEC2AutoScalingGroups",
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["autoscaling:DescribeAutoScalingGroups",
                     "autoscaling:DeleteAutoScalingGroup",                    
            ]        
        ))

        # Add policy to Lamda Execution role to list and delete ELB and Target groups
        my_lambda.add_to_role_policy(iam.PolicyStatement(
            sid="AllowToListAndDeleteELB",
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["elasticloadbalancing:DeleteLoadBalancer",
                     "elasticloadbalancing:DescribeLoadBalancers",
                     "elasticloadbalancing:DescribeListeners",
                     "elasticloadbalancing:DescribeTargetGroups",
                     "elasticloadbalancing:DeleteTargetGroup",
                     "elasticloadbalancing:DeleteListener"
                     ]
        ))

        # Create schedule event to invoke lamda
        my_cron = os.getenv("CRON", "cron(0/15 * * * ? *)")
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
