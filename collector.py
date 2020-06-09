import os
import json
from csv import reader
from datetime import datetime
from dateutil.relativedelta import relativedelta
from googleapiclient.discovery import build
from data_processing.detect_face import detect_face


def check_channel_id(channels_list: list, path: str) -> list:
    """
    Checks if there exists data for the provided channel ids in the 
    directory (path arg), assuming the directory contains files of format
    <channel_id>.<ext>
    Args:
    - channel_ids: a list of channel ids
    - path: path to the directory to check

    Returns a filtered list of channel_ids that were not found in the directory.
    """
    channels_in_dir = os.listdir(path)
    # remove the file extension for the files in the dir
    channels_in_dir = [
        os.path.splitext(channel)[0] for channel in channels_in_dir
    ]

    to_remove = []
    # do a lookup of the channel id in the directory to see if a file already exists
    for channel_id in channels_list:
        if channel_id in channels_in_dir:
            to_remove.append(channel_id)

    # remove the channel id from the list
    [channels_list.remove(channel_id) for channel_id in to_remove]

    return channels_list


def get_response_item(resource_property: str, key: str, channel_id: str, path: str):
    """
    Get the value for the key in the resource_property dict for the provided 
    channel_id and path.
    Args:
    - resource_property: a key in the response dict corresponding to the resource property ('part') to search
    - key: key to search for in the resource_property dict
    - channel_id: channel id
    - path: directory to search; must end with trailing /
    """
    ext = '.json'
    with open(path+channel_id+ext) as response:
        data = json.load(response)

    item = data[resource_property][key]

    return item


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


def get_channel_details(service, channel_ids: str, part='snippet,statistics,brandingSettings', results=50):
    """
    Makes use of the channel resource list method. Gets channel data for 
    resource properties defined in the part argument and writes the repsonse
    to JSON files in data/channels

    Args:
    - service: The YouTube Data API service
    - channel_ids: A comma-separated string of the YouTube channel ID(s)
    - part: A comma-separated string of channel resource properties
    - results: Max results returned in the reponse
    """
    channel_detail = service.channels()
    # split string into list of channel ids
    channels_list = channel_ids.split(',')
    channels_path = 'data/channels/'

    # get list of channels for which there is no data in the channels_path dir
    channels_list = check_channel_id(channels_list, channels_path)

    if channels_list:
        # take list of filtered channel ids -> string of comma-separated ids
        channel_ids = ",".join(channels_list)
        # make the request to the resource
        request = channel_detail.list(
            part=part, id=channel_ids, maxResults=results
        )
        response = request.execute()
        response_items = response['items']
        # want to write a folder with the channel id to channels_path
        # that holds .json files of the response for each channel id
        for channel in response_items:  # channel is a dict of channel data
            with open(channels_path+'{}.json'.format(channel['id']), 'w+') as channel_data:
                response_obj = json.dumps(channel)
                channel_data.write(response_obj)


# TODO: - implement some sort of logging of the response
#       - add exception handling
def get_channel_videos(service, channel_id: str, part='snippet', type='video', results=50):
    """
    Get video data associated with a channel id and write the response to a JSON
    file in data/videos.
    """
    yt_search = service.search()

    videos_path = 'data/videos/data/unit_channel/'
    channels_path = 'data/channels/'
    channel = check_channel_id([channel_id], videos_path)

    final_out = {}
    if channel:
        # how many videos the channel has
        video_ct = get_response_item(
            'statistics', 'videoCount', channel_id, channels_path
        )
        # the date the channel was created
        year_pub = get_response_item(
            'snippet', 'publishedAt', channel_id, channels_path
        )
        year_pub = datetime.strptime(year_pub, "%Y-%m-%dT%H:%M:%S%z").year

        if int(video_ct) > 500:
            for year in range(year_pub, datetime.today().year+1):
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
        else:
            # TODO: refactor
            request = yt_search.list(part=part,
                                     channelId=channel_id,
                                     type=type,
                                     maxResults=results
                                     )
            response = request.execute()

            # full response output for the year
            data_out = page_through_response(yt_search, request, response)

            final_out = data_out

        with open(videos_path+'{}.json'.format(channel_id), 'w+') as video_data:
            response_obj = json.dumps(final_out)
            video_data.write(response_obj)


def get_video_details():
    pass


def main():
    with open('secrets.json', 'r') as key:
        secrets = json.load(key)

    API_KEY = secrets['API_KEY']
    API_SERVICE_NAME = 'youtube'
    API_VERSION = 'v3'

    service = build(API_SERVICE_NAME, API_VERSION, developerKey=API_KEY)

    # read channel ids from file
    with open('channels.csv', 'r') as f:
        csv_reader = reader(f)
        next(csv_reader)  # skip header
        rows = list(csv_reader)
    # store channel ids in a list
    channels = [row[0] for row in rows]

    channels_str = ",".join(channels)
    get_channel_details(service, channels_str)

    for channel in channels:
        get_channel_videos(service, channel)


if __name__ == "__main__":
    main()
