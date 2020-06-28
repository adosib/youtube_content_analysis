import os
import json
import logging
from csv import reader
from datetime import datetime
from dateutil.relativedelta import relativedelta
from googleapiclient.discovery import build
from data_processing.detect_face import detect_face

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s:%(funcName)s:%(message)s'
)
file_handler = logging.FileHandler("collector.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


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

    logger.info("Filtering {} out of {} provided channels".format(
        len(to_remove), len(channels_list)
    ))

    # remove the channel id from the list
    [channels_list.remove(channel_id) for channel_id in to_remove]

    logger.info("The following channels remain: {}.".format(channels_list))

    return channels_list


def get_response_item(resource_property: str, key: str, channel_id: str, path: str, ext='.json'):
    """
    Get the value for the key in the resource_property dict for the provided
    channel_id and path.
    Args:
    - resource_property: a key in the response dict corresponding to the resource property ('part') to search
    - key: key to search for in the resource_property dict
    - channel_id: channel id
    - path: directory to search; must end with trailing /
    """
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

    counter = 0
    while response['items']:

        previous_request = request
        previous_response = response

        request = service_instance.list_next(previous_request=previous_request,
                                             previous_response=previous_response)
        try:
            response = request.execute()
            counter += 1
            logger.info(
                "This is paging request number {} for the resource {}.".format(
                    counter, response["kind"]
                )
            )
        except AttributeError:
            logger.exception(
                "Paging request failed for request {}.".format(request)
            )
            break

        # add the items from the response to output
        output['items'].extend(response['items'])
        logger.info(
            "{} values have been added to the reponse object's 'items' key."
            .format(len(response['items']))
        )

    return output


def get_channel_details(service, channels: list, part='snippet,statistics,brandingSettings', results=50):
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

    channels_path = 'data/channels/'

    # get list of channels for which there is no data in the channels_path dir
    channels_list = check_channel_id(channels, channels_path)

    if channels_list:
        # take list of filtered channel ids -> string of comma-separated ids
        channel_ids = ",".join(channels_list)
        # make the request to the resource
        request = channel_detail.list(
            part=part, id=channel_ids, maxResults=results
        )
        try:
            response = request.execute()
            logger.info(
                "Successfully made a request to the channels resource with channel ids {}.". format(
                    channel_ids
                )
            )
            response_items = response['items']
            # want to write a folder with the channel id to channels_path
            # that holds .json files of the response for each channel id
            for channel in response_items:  # channel is a dict of channel data
                with open(channels_path+'{}.json'.format(channel['id']), 'w+') as channel_data:
                    response_obj = json.dumps(channel)
                    channel_data.write(response_obj)
                    logger.info(
                        "Wrote channel data for channel id {}.".format(
                            channel['id']
                        )
                    )
        except Exception:
            logger.exception(
                "The request to the channels resource failed."
            )


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
        logger.info(
            "Retrieving video data for channel id {}.".format(channel_id)
        )
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

                try:
                    response = request.execute()
                except Exception:
                    logger.exception(
                        "The request to the search resource failed."
                    )

                # full response output for the year
                data_out = page_through_response(
                    yt_search, request, response
                )

                # build on the items list in the final_out dict to form the complete response
                if final_out:
                    final_out['items'].extend(data_out['items'])
                else:
                    final_out = data_out
        else:
            request = yt_search.list(part=part,
                                     channelId=channel_id,
                                     type=type,
                                     maxResults=results
                                     )
            try:
                response = request.execute()
            except Exception:
                logger.exception(
                    "The request to the search resource failed."
                )

            # full response output for the year
            data_out = page_through_response(yt_search, request, response)

            final_out = data_out

        with open(videos_path+'{}.json'.format(channel_id), 'w+') as video_data:
            response_obj = json.dumps(final_out)
            video_data.write(response_obj)


def check_video_id():
    pass


# def get_video_details(service, part='snippet,contentDetails,statistics,topicDetails', results=50):
#     """
#     Loop through files in data/videos/unit_channel to get the videoId inside of each objects
#     in the items list. Use this id to request data from the videos resource to get statistics
#     on each video.
#     """
#     video_detail = service.videos()
#     video_ids = check_video_id()  # str of comma-sep video ids
#     video_detail.list(part=part, id=video_ids, maxResults=results)


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

    # channels_str=",".join(channels)  # store in comma-separated string
    get_channel_details(service, channels)

    for channel in channels:
        print(channels)
        get_channel_videos(service, channel)


if __name__ == "__main__":
    main()
