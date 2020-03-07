FROM python:3.6
ADD . /code
WORKDIR /code
RUN pip install -r requirements.txt
CMD exec gunicorn -k gevent -b 0.0.0.0:$PORT asr:app
