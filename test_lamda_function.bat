rem Run CDK synth to generate CloudFormation template
call  cdk synth --no-staging
rem Run Lamda test
call  sam local invoke TerminateLongRunningAwsResourcesFunction --no-event -t ./cdk.out/TerminateLongRunningAwsResourcesStack.template.json