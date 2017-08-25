FROM python:2.7 

RUN mkdir /app
WORKDIR /app

ADD requirements.txt /app

RUN pip install -r requirements.txt

COPY docker-entrypoint.sh /docker-entrypoint.sh

RUN chmod +x /docker-entrypoint.sh


