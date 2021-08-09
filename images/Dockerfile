FROM public.ecr.aws/lambda/python:3.8

COPY requirements.txt ./
RUN pip3 install -r requirements.txt

COPY . .

# This will be overrided by the 'command' in your functions generic.yml. 

#CMD ["handler.run"]