import json
import os
import boto3

AMI_ID = os.environ["AMI_ID"]
INSTANCE_TYPE = os.environ["INSTANCE_TYPE"]
KEY_NAME = os.environ["KEY_NAME"]
REGION = os.environ["REGION"]

ec2 = boto3.client("ec2", region_name=REGION)


def run(event, context):
    unparsed_subreddit_group = str(event["Records"][0]["body"])

    init_script = """
                    #!/bin/bash

                    cd /home/ec2-user

                    python3 -m venv .venv
                    source .venv/bin/activate

                    eval $(ssh-agent -s)
                    ssh-keyscan github.com >> ~/.ssh/known_hosts

                    #Grab private key from s3 bucket
                    aws s3 cp s3://whodoesntlovereddit-keys/gh_dining .

                    #Change permissions and add the key to use it.
                    chmod 400 ./gh_dining
                    ssh-add ./gh_dining

                    #Update and install git
                    sudo yum update -y
                    sudo yum install git -y

                    git clone git@github.com:diningPhilosopher64/whodoesntlovereddit.git
                """

    # shutdown -h +5

    instance = ec2.run_instances(
        ImageId=AMI_ID,
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_NAME,
        SecurityGroups=["ssh-access"],
        DisableApiTermination=False,
        MaxCount=1,
        MinCount=1,
        InstanceInitiatedShutdownBehavior="terminate",
        UserData=init_script,
        IamInstanceProfile={"Name": "EC2-render-video-upload-to-s3"},
    )

    instance_id = instance["Instances"][0]["InstanceId"]
    print(instance_id)

    return instance_id
