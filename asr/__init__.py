import gevent.monkey
gevent.monkey.patch_all()
import base64
from email.mime.multipart import MIMEMultipart
from email.message import Message
import json
import struct
import os

import requests
from flask import Flask, request, Response, abort

app = Flask(__name__)

AUTH_URL = "https://auth.rebble.io"
API_KEY = os.environ['SPEECH_API_KEY']


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
            if frame != b'':
                header, content = frame.split(b'\r\n\r\n', 1)
                yield content[:-2]
            this_frame = this_frame[end + len(boundary):]
        if content == b'':
            print("End of input.")
            break


@app.route('/NmspServlet/', methods=["POST"])
def recognise():
    stream = request.stream

    access_token, part1, part2 = request.host.split('.', 1)[0].split('-', 3)
    lang = f"{part1}-{part2.upper()}"

    auth_req = requests.get(f"{AUTH_URL}/api/v1/me/token", headers={'Authorization': f"Bearer {access_token}"})
    if not auth_req.ok:
        abort(401)

    chunks = iter(list(parse_chunks(stream)))
    content = next(chunks).decode('utf-8')

    body = {
        'config': {
            'encoding': 'SPEEX_WITH_HEADER_BYTE',
            'language_code': lang,
            'sample_rate_hertz': 16000,
            'max_alternatives': 1,
            # 'metadata': {
            #     'interaction_type': 'DICTATION',
            #     'microphone_distance': 'NEARFIELD',
            # },
        },
        'audio': {
            'content': base64.b64encode(b''.join((struct.pack('B', len(x)) + x for x in chunks))).decode('utf-8'),
        },
    }
    result = requests.post(f'https://speech.googleapis.com/v1/speech:recognize?key={API_KEY}', json=body)
    result.raise_for_status()

    words = []
    if 'results' in result.json():
        for result in result.json()['results']:
            words.extend({
                             'word': x,
                             'confidence': result['alternatives'][0]['confidence']
                         } for x in result['alternatives'][0]['transcript'].split(' '))

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

    response = Response(parts.as_string().split("\n", 3)[3])
    response.headers['Content-Type'] = f'multipart/form-data; boundary={parts.get_boundary()}'
    return response

