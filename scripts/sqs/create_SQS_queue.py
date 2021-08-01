import boto3, click, pprint

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)
sqs = boto3.resource('sqs')

@click.command()
@click.option('--name', type=str, help="Name of the SQS Queue")
def main(name):
	queue_name = name
	print(f"\n ###### Creating an SQS Queue with name: {queue_name}  ######\n")
	response = sqs.create_queue(QueueName=queue_name)
	pp.pprint(response)
	

if __name__=='__main__':
	main()