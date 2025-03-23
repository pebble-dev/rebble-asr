import gevent.monkey
gevent.monkey.patch_all()
from email.mime.multipart import MIMEMultipart
from email.message import Message
from .model_map import get_model_for_lang
import json
import os
from speex import SpeexDecoder
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

import grpc.experimental.gevent as grpc_gevent
grpc_gevent.init_gevent()

import requests
from flask import Flask, request, Response, abort
import logging
import datetime

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

AUTH_URL = os.environ.get("AUTH_URL", "https://auth.rebble.io")

speech_client = SpeechClient(
    client_options={"api_endpoint": "us-central1-speech.googleapis.com"}
)

# We know gunicorn does this, but it doesn't *say* it does this, so we must signal it manually.
@app.before_request
def handle_chunking():
    request.environ['wsgi.input_terminated'] = 1



def parse_chunks(stream):
    boundary = b'--' + request.headers['content-type'].split(';')[1].split('=')[1].encode('utf-8').strip()  # super lazy/brittle parsing.
    this_frame = b''
    while True:
        content = stream.read(4096)
        this_frame += content
        end = this_frame.find(boundary)
        if end > -1:
            frame = this_frame[:end]
            this_frame = this_frame[end + len(boundary):]
            if frame != b'':
                try:
                    header, content = frame.split(b'\r\n\r\n', 1)
                except ValueError:
                    continue
                yield content[:-2]
        if content == b'':
            print("End of input.")
            break


@app.route('/heartbeat')
def heartbeat():
    return 'asr'

@app.route('/NmspServlet/', methods=["POST"])
def recognise():
    stream = request.stream

    access_token, lang = request.host.split('.', 1)[0].split('-', 1)

    auth_req = requests.get(f"{AUTH_URL}/api/v1/me/token", headers={'Authorization': f"Bearer {access_token}"})
    if not auth_req.ok:
        abort(401)

    lang = model_map.get_real_lang(lang)

    req_start = datetime.datetime.now()
    logging.info("Received transcription request in language: %s", lang)
    chunks = iter(list(parse_chunks(stream)))
    logging.info("Audio received in %s", datetime.datetime.now() - req_start)
    content = next(chunks).decode('utf-8')

    decode_start = datetime.datetime.now()
    decoder = SpeexDecoder(1)
    pcm = bytearray()
    for chunk in chunks:
        pcm.extend(decoder.decode(chunk))
    logging.info("Decoded speex in %s", datetime.datetime.now() - decode_start)

    asr_request_start = datetime.datetime.now()
    config = cloud_speech.RecognitionConfig(
        explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
            encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            audio_channel_count=1,
        ),
        language_codes=[lang],
        features=cloud_speech.RecognitionFeatures(
            profanity_filter=True, # matches current behaviour, but do we really want it?
            enable_word_confidence=True, # Pebble uses (ignores) this
            enable_automatic_punctuation=True,
            max_alternatives=1,
        ),
        model="chirp_2",
    )

    asr_request = cloud_speech.RecognizeRequest(
        recognizer=f"projects/pebble-rebirth/locations/us-central1/recognizers/_",
        config=config,
        content=bytes(pcm),
    )
    response = speech_client.recognize(asr_request, timeout=5)
    logging.info("ASR request completed in %s", datetime.datetime.now() - asr_request_start)

    words = []
    for result in response.results:
        words.extend({
                         'word': x,
                         'confidence': str(result.alternatives[0].confidence),
                     } for x in result.alternatives[0].transcript.split(' '))

    # Now for some reason we also need to give back a mime/multipart message...
    parts = MIMEMultipart()
    response_part = Message()
    response_part.add_header('Content-Type', 'application/JSON; charset=utf-8')

    if len(words) > 0:
        response_part.add_header('Content-Disposition', 'form-data; name="QueryResult"')
        words[0]['word'] += '\\*no-space-before'
        words[0]['word'] = words[0]['word'][0].upper() + words[0]['word'][1:]
        response_part.set_payload(json.dumps({
            'words': [words],
        }))
    else:
        response_part.add_header('Content-Disposition', 'form-data; name="QueryRetry"')
        # Other errors probably exist, but I don't know what they are.
        # This is a Nuance error verbatim.
        response_part.set_payload(json.dumps({
            "Cause": 1,
            "Name": "AUDIO_INFO",
            "Prompt": "Sorry, speech not recognized. Please try again."
        }))
    parts.attach(response_part)

    parts.set_boundary('--Nuance_NMSP_vutc5w1XobDdefsYG3wq')

    response = Response('\r\n' + parts.as_string().split("\n", 3)[3].replace('\n', '\r\n'))
    response.headers['Content-Type'] = f'multipart/form-data; boundary={parts.get_boundary()}'
    logging.info("Request complete in %s", datetime.datetime.now() - req_start)
    return response
