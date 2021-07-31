import boto3, pprint

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)
sns = boto3.client('sns')

def main():
	topics = sns.list_topics()['Topics']

	pp.pprint(topics)


if __name__=="__main__":
	main()