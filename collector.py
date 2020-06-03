import json
import logging
from googleapiclient.discovery import build


logger = logging.getLogger()
logger.setLevel(logging.INFO)

with open('secrets.json', 'r') as key:
    secrets = json.load(key)

API_KEY = secrets['API_KEY']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

service = build(API_SERVICE_NAME, API_VERSION, developerKey=API_KEY)

request = service.search().list(
    part='snippet',
    channelId='UCCezIgC97PvUuR4_gbFUs5g',
    type='video'
)

result = request.execute()

print(result)
