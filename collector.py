import os
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


def get_channel_details(service, channel_ids, part='snippet,statistics,brandingSettings', results=50):
    """
    Makes use of the channel resource list method. 
    Args:
    - service: The YouTube Data API service
    - channel_ids: A comma-separated list of the YouTube channel ID(s)
    - part: A comma-separated string of channel resource properties
    - results: Max results returned in the reponse

    Returns the following data:
    - snippet.publishedAt: The date and time that the channel was created
    - statistics.viewCount: The number of times the channel has been viewed
    - statistics.commentCount: The number of comments for the channel
    - statistics.subscriberCount: The number of subscribers that the channel has
    - statistics.videoCount: The number of videos uploaded to the channel
    - brandingSettings.channel.keywords: Space-separated list of keywords associated w/ the channel
    """
    channel_detail = service.channels()
    # split string into list of channel ids
    channel_ids = channel_ids.split(',')
    channels_path = 'data/channels/'

    channels_in_dir = os.listdir(channels_path)
    # remove the file extension for the files in the dir
    channels_in_dir = [os.path.splitext(channel)[0]
                       for channel in channels_in_dir]

    to_remove = []
    # do a lookup of the channel id in the /data/channels directory to see if a folder already exists
    for channel in channel_ids:
        if channel in channels_in_dir:
            to_remove.append(channel)

    # remove the channel id from the list
    [channel_ids.remove(channel) for channel in to_remove]

    if channel_ids:
        # re-join channel ids into comma-separated string
        channel_ids = ",".join(channel_ids)
        # make the request to the resource
        request = channel_detail.list(
            part=part, id=channel_ids, maxResults=results
        )
        response = request.execute()
        response_items = response['items']
        # want to write a folder with the channel id to /data/channels
        # that holds .json files of the response for each channel id
        for channel in response_items:  # channel is a dict of channel data
            with open(channels_path+'{}.json'.format(channel['id']), 'w+') as channel_data:
                response_obj = json.dumps(channel)
                channel_data.write(response_obj)


# TODO: - implement some sort of logging of the response
#       - add exception handling
def get_channel_videos(service, channel_id, part='snippet', type='video', results=50):
    yt_search = service.search()

    final_out = {}
    # TODO: a call to the channel resource (part='statistics') will greatly reduce the need for
    #       this sort of looping which is resource intensive on the API
    #       because I will be able to see the video count from there and make a conditional
    #       NOTE this can be done in ONE call by passing a string of comma-separated channel ids to the id parameter
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
    channels = ['UCfzlCWGWYyIQ0aLC5w48gBQ',
                'UCCUw_xsps3VgtqLYR8vBSXw',
                'UCCezIgC97PvUuR4_gbFUs5g',
                'UC_ML5xP23TOWKUcc-oAE_Eg']

    channels_str = ",".join(channels)
    get_channel_details(service, channels_str)

    # for channel in channels:
    #     get_channel_videos(service, channel)


if __name__ == "__main__":
    main()
