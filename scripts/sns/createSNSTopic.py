import boto3, click, pprint

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)
client = boto3.client('sns')

@click.command()
@click.option('--name', type=str, help="Name of the SNS topic")
def main(name):
	topic_name = name
	print(f"\n ###### Creating an SNS Topic with name: {topic_name}  ######\n")
	response = client.create_topic(Name=topic_name)
	pp.pprint(response)
	

if __name__=='__main__':
	main()

