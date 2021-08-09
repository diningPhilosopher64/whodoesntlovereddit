FROM public.ecr.aws/lambda/python:3.8

COPY requirements.txt /var/task
RUN pip3 install -r /var/task/requirements.txt

COPY . .

# This will be overrided by the 'command' in your functions generic.yml. 

CMD ["daily_uploads_gather_urls.run"]