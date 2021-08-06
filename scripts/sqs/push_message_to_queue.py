import boto3, click, pprint

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)
sqs = boto3.client('sqs')

@click.command()
@click.option('--name', type=str, help="Name of the SQS Queue")
@click.option('--message', type=str, help="Message content as a string")
def main(name, message):
	queue_name = name
	queue_url = sqs.get_queue_url(QueueName=queue_name)['QueueUrl']
	print(f"\n ###### Pushing message: {message} to SNS Queue: {queue_name}  ######\n")
	print(f"\n QueueName:{queue_name}\n QueueUrl: {queue_url}\n")
	response = sqs.send_message(QueueUrl=queue_url, MessageBody=message)
	pp.pprint(response)
	

if __name__=='__main__':
	main()