from email.mime.multipart import MIMEMultipart
from email.message import Message
import json
import struct

from flask import Flask, request, Response
from google.cloud import speech


app = Flask(__name__)


# We know gunicorn does this, but it doesn't *say* it does this, so we must signal it manually.
@app.before_request
def handle_chunking():
    request.environ['wsgi.input_terminated'] = 1


def parse_chunks(stream):
    boundary = b'--' + request.headers['content-type'].split(';')[1].split('=')[1].encode('utf-8').strip()  # super lazy/brittle parsing.
    print("Boundary: " + boundary.decode('utf-8'))
    this_frame = b''
    while True:
        content = stream.read(4096)
        this_frame += content
        end = this_frame.find(boundary)
        if end > -1:
            frame = this_frame[:end]
            if frame != b'':
                header, content = frame.split(b'\r\n\r\n', 1)
                print(content)
                yield content[:-2]
            this_frame = this_frame[end + len(boundary):]
        if content == b'':
            print("End of input.")
            break


def parse_data():
    boundary = b'--' + request.headers['content-type'].split(';')[1].split('=')[1].encode('utf-8').strip()  # super lazy/brittle parsing.
    parts = request.data.split(boundary)
    for part in parts:
        if part == b'':
            continue
        yield part.split(b'\r\n\r\n', 1)[1][:-2]


@app.route('/NmspServlet/', methods=["POST"])
def recognise():

    client = speech.SpeechClient()
    stream = request.stream
    chunks = iter(list(parse_chunks(stream)))
    content = next(chunks).decode('utf-8')
    print(content)

    config = speech.types.RecognitionConfig(
        encoding='SPEEX_WITH_HEADER_BYTE',
        language_code='en-US',
        sample_rate_hertz=16000,
    )
    print('beginning request')
    responses = client.streaming_recognize(
        config=speech.types.StreamingRecognitionConfig(config=config),
        requests=(
            speech.types.StreamingRecognizeRequest(audio_content=struct.pack('B', len(x)) + x)
            for x in chunks))
    print('finished request')
    words = []
    for response in responses:
        if response.results:
            for result in response.results:
                words.extend({
                                 'word': x,
                                 'confidence': result.alternatives[0].confidence
                             } for x in result.alternatives[0].transcript.split(' '))

    # Now for some reason we also need to give back a mime/multipart message...
    parts = MIMEMultipart()
    response_part = Message()
    response_part.add_header('Content-Type', 'application/JSON; charset=utf-8')

    if len(words) > 0:
        response_part.add_header('Content-Disposition', 'form-data; name="QueryResult"')
        words[0]['word'] += '\\*no-space-before'
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
    print(parts.as_string())

    response = Response(parts.as_string().split("\n", 3)[3])
    response.headers['Content-Type'] = f'multipart/form-data; boundary={parts.get_boundary()}'
    response.headers['Connection'] = 'close'
    return response

