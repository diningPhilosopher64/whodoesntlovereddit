import boto3, click, pprint

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)
sqs = boto3.client('sqs')

@click.command()
@click.option('--name', type=str, help="Name of the SQS Queue")
def main(name):
	queue_name = name
	queue_url = sqs.get_queue_url(QueueName=queue_name)['QueueUrl']
	print(f"\n ###### State of SNS Queue: {queue_name}  ######\n")
	response = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])
	pp.pprint(response)
	

if __name__=='__main__':
	main()