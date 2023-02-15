rem Run CDK synth to generate CloudFormation template
@REM call  cdk synth --no-staging
call  cdk synth
rem Run Lamda test
call  sam local invoke TerminateLongRunningAwsResourcesFunction --no-event -t ./cdk.out/TerminateLongRunningAwsResourcesStack.template.json