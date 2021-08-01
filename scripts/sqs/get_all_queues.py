import boto3, pprint

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)
sqs = boto3.client('sqs')

def main():	
	print(f"\n ###### Fetching all SQS Queues ######\n")
	response = sqs.list_queues()['QueueUrls']
	pp.pprint(response)
	

if __name__=='__main__':
	main()