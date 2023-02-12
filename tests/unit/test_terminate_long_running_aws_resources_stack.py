import aws_cdk as core
import aws_cdk.assertions as assertions

from terminate_long_running_aws_resources.terminate_long_running_aws_resources_stack import TerminateLongRunningAwsResourcesStack

# example tests. To run these tests, uncomment this file along with the example
# resource in terminate_long_running_aws_resources/terminate_long_running_aws_resources_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = TerminateLongRunningAwsResourcesStack(app, "terminate-long-running-aws-resources")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
