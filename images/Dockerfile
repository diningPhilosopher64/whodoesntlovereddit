FROM public.ecr.aws/lambda/python:3.8

# RUN yum install wget -y

RUN yum -y update && \
    yum -y install wget && \
    yum install -y tar.x86_64 && \
    yum install -y xz \
    yum clean all



# RUN mkdir /usr/local/ffmpeg 

# RUN wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz

# RUN tar -xf ffmpeg-release-amd64-static.tar.xz

# RUN mv ffmpeg/ffmpeg-release-amd64-static/ffmpeg .

# RUN ln -s ffmpeg /usr/bin/ffmpeg


################################################

RUN mkdir /usr/local/bin/ffmpeg 


RUN wget -P /usr/local/bin/ffmpeg  https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar -xvf /usr/local/bin/ffmpeg/ffmpeg-release-amd64-static.tar.xz --directory /usr/local/bin/ffmpeg  

RUN mv /usr/local/bin/ffmpeg/ffmpeg-4.4-amd64-static/ffmpeg /usr/local/bin/ffmpeg/

RUN ln -s /usr/local/bin/ffmpeg/ffmpeg /usr/bin/ffmpeg

RUN rm -rf /usr/local/bin/ffmpeg/ffmpeg-release-amd64-static && \
    rm -rf /usr/local/bin/ffmpeg/ffmpeg-release-amd64-static.tar.xz

# RUN ffmpeg

RUN cd /var/task/

COPY requirements.txt /var/task

RUN pip3 install -r /var/task/requirements.txt

COPY . .

# # This will be overrided by the 'command' in your functions generic.yml. 
CMD ["daily_uploads_gather_urls.run"]