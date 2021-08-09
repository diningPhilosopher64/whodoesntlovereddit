FROM public.ecr.aws/lambda/python:3.8

COPY handler.py ./
COPY __init__.py ./
COPY requirements.txt ./
COPY ./lib ./lib

RUN pip3 install -r requirements.txt

RUN ls
RUN ls lib/
RUN ls lib/db/
RUN cat lib/db/__init__.py

CMD ["handler.run"]