import json
from time import sleep
from googleapiclient.discovery import build


# TODO: - implement some sort of logging of the response
#       - add exception handling
#       - figure out how to get > 500 results
def get_channel_videos(service, channel_id, part='snippet', type='video', results=50):
    yt_search = service.search()
    request = yt_search.list(part=part, channelId=channel_id,
                             type=type, maxResults=results)
    response = request.execute()
    output = response

    while response['items']:
        previous_request = request
        previous_response = response

        request = yt_search.list_next(previous_request=previous_request,
                                      previous_response=previous_response)
        response = request.execute()

        # add the items from the response to the items list
        output['items'].extend(response['items'])

    with open('out.json', 'a+') as video_data:
        response_obj = json.dumps(output)
        video_data.write(response_obj)


def main():
    with open('secrets.json', 'r') as key:
        secrets = json.load(key)

    API_KEY = secrets['API_KEY']
    API_SERVICE_NAME = 'youtube'
    API_VERSION = 'v3'

    service = build(API_SERVICE_NAME, API_VERSION, developerKey=API_KEY)
    channels = ['UCfzlCWGWYyIQ0aLC5w48gBQ']  # sentdex

    for channel in channels:
        get_channel_videos(service, channel)


if __name__ == "__main__":
    main()
