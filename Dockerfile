FROM python:3.13-alpine
RUN apk add --no-cache speex speexdsp speex-dev speexdsp-dev git build-base
RUN git clone https://github.com/pebble-dev/pyspeex.git && pip install cython setuptools && cd pyspeex && make && python setup.py install && cd .. && rm -rf pyspeex
RUN apk del --no-cache speex-dev speexdsp-dev git
COPY requirements.txt /requirements.txt
RUN pip install -r requirements.txt
RUN apk del --no-cache build-base
ADD . /code
WORKDIR /code
CMD exec gunicorn -k gevent -b 0.0.0.0:$PORT asr:app
