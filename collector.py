import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
from googleapiclient.discovery import build


# TODO: refactor into a class YTVideoSearch
def page_through_response(service_instance, request, response) -> dict:
    """
    Pages through a response by calling on the list_next method of the service instance.
    Returns the full response dictionary.
    """
    output = response
    while response['items']:

        previous_request = request
        previous_response = response

        request = service_instance.list_next(previous_request=previous_request,
                                             previous_response=previous_response)
        try:
            response = request.execute()
        except AttributeError:
            break
        # add the items from the response to output
        output['items'].extend(response['items'])

    return output


# TODO: - implement some sort of logging of the response
#       - add exception handling
#       - figure out date of first-published video or yt channel activation
def get_channel_videos(service, channel_id, part='snippet', type='video', results=50):
    yt_search = service.search()

    final_out = {}
    for year in range(2000, datetime.today().year+1):
        start = datetime(year, 1, 1)
        end = start + relativedelta(years=1)
        # prepare dates in a format the YT API is happy with
        start, end = [date.isoformat('T')+'Z' for date in [start, end]]

        request = yt_search.list(part=part,
                                 channelId=channel_id,
                                 type=type,
                                 publishedAfter=start,
                                 publishedBefore=end,
                                 maxResults=results
                                 )
        response = request.execute()

        # full response output for the year
        data_out = page_through_response(yt_search, request, response)

        # build on the items list in the final_out dict to form the complete response
        if final_out:
            final_out['items'].extend(data_out['items'])
        else:
            final_out = data_out

    with open('out1.json', 'a+') as video_data:
        response_obj = json.dumps(final_out)
        video_data.write(response_obj)


def get_video_thumbnails(img_url):
    pass


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
