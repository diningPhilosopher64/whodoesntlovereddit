import boto3, click, pprint

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)
sns = boto3.client('sns')
my_session = boto3.session.Session()
my_region = my_session.region_name
my_accountId = boto3.client('sts').get_caller_identity().get('Account')

@click.command()
@click.option('--name', type=str, help="Name of the SNS topic to delete")
def main(name):
	topic_name = name
	topic_arn = f"arn:aws:sns:{my_region}:{my_accountId}:{topic_name}"
	print(f"\n ###### Deleting SNS Topic with name: {topic_name}  ######\n")
	response = sns.delete_topic(TopicArn=topic_arn)
	pp.pprint(response)
	

if __name__=='__main__':
	main()