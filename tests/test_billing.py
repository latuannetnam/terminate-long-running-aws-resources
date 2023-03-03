import boto3

# Create a Cost Explorer client
ce = boto3.client('ce')

# Set time range to cover the last full calendar month
time_period = {
    'Start': '2023-02-01',
    'End': '2023-03-01'
}

# Set granularity to MONTHLY
#granularity = 'MONTHLY'
granularity = 'DAILY'

# Set metrics to BlendedCost and UsageQuantity
metrics = ['BlendedCost', 'UsageQuantity']

# Get cost and usage data
response = ce.get_cost_and_usage(
    TimePeriod=time_period,
    Granularity=granularity,
    Metrics=metrics
)

# Print cost and usage data
for result in response['ResultsByTime']:
    print(result['TimePeriod']['Start'], result['Total'])