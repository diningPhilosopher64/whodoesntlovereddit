import boto3, click, pprint

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)
sqs = boto3.client('sqs')

@click.command()
@click.option('--name', type=str, help="Name of the SQS Queue")
def main(name):
	queue_name = name
	queue_url = sqs.get_queue_url(QueueName=queue_name)['QueueUrl']
	print(f"\n###### Deleting all messages in the SQS Queue: {queue_name} ######\n")
	response = sqs.purge_queue(QueueUrl=queue_url)
	pp.pprint(response)
	

if __name__=='__main__':
	main()