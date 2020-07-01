import os
import json
import logging
from csv import reader
from datetime import datetime
from dateutil.relativedelta import relativedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from data_processing.detect_face import detect_face_v2

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s:%(funcName)s:%(message)s'
)
file_handler = logging.FileHandler("collector.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def filter_channel_or_video(ids: list, path: str) -> list:
    """
    Checks if there exists data for the provided channel or video ids in the
    directory (path arg), assuming the directory contains files of format
    <id>.<ext>
    Args:
    - ids: a list of channel or video ids
    - path: path to the directory to check

    Returns a filtered list of ids that were not found in the directory.
    """
    all_files = os.listdir(path)
    # remove the file extension for the files in the dir
    all_files = [
        os.path.splitext(file_id)[0] for file_id in all_files
    ]

    # create a copy of the list to avoid mutating the original
    filtered = ids.copy()
    to_remove = []
    # do a lookup of the id in the directory to see if a file already exists
    for file_id in filtered:
        if file_id in all_files:
            to_remove.append(file_id)

    logger.info("Filtering {} out of {} provided ids".format(
        len(to_remove), len(filtered)
    ))

    # remove the id from the list
    [filtered.remove(id) for id in to_remove]

    return filtered


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
    while response['items'] and len(response['items']) >= 50:

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
    channels_list = filter_channel_or_video(channels, channels_path)

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

    channel_videos_path = 'data/videos/data/unit_channel/'
    channels_path = 'data/channels/'
    channel = filter_channel_or_video([channel_id], channel_videos_path)

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
            logger.info(
                "The channel with id {} has >500 ({}) videos. Entering request loop.".format(
                    channel_id, video_ct
                )
            )
            for year in range(year_pub, datetime.today().year+1):
                start = datetime(year, 1, 1)
                end = start + relativedelta(years=1)
                # prepare dates in a format the YT API is happy with
                start, end = [date.isoformat('T')+'Z' for date in [start, end]]

                logger.info(
                    "Requesting from the search resource with publishedAfter={} and publishedBefore={}.".format(
                        start, end
                    )
                )

                request = yt_search.list(part=part,
                                         channelId=channel_id,
                                         type=type,
                                         publishedAfter=start,
                                         publishedBefore=end,
                                         maxResults=results
                                         )

                try:
                    response = request.execute()
                except HttpError:
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
            logger.info(
                "The channel with id {} has <=500 ({}) videos. Sending request to the search resource.".format(
                    channel_id, video_ct
                )
            )
            request = yt_search.list(part=part,
                                     channelId=channel_id,
                                     type=type,
                                     maxResults=results
                                     )
            try:
                response = request.execute()
            except HttpError:
                logger.exception(
                    "The request to the search resource failed."
                )

            # full response output for the year
            data_out = page_through_response(yt_search, request, response)

            final_out = data_out

        with open(channel_videos_path+'{}.json'.format(channel_id), 'w+') as video_data:
            response_obj = json.dumps(final_out)
            video_data.write(response_obj)


def get_video_details(service, part='snippet,contentDetails,statistics,topicDetails', results=50):
    """
    Loop through files in data/videos/unit_channel to get the videoId inside of each objects
    in the items list. Use this id to request data from the videos resource to get statistics
    on each video.
    """
    channel_videos_path = 'data/videos/data/unit_channel/'
    videos_path = 'data/videos/data/unit_video/'

    video_ids = []
    # parse through json files to get all video ids
    with os.scandir(channel_videos_path) as channel_vids:
        for channel in channel_vids:
            with open(channel, 'r') as videos:
                response = json.load(videos)
                for item in response['items']:
                    video_ids.append(item['id']['videoId'])

    # filter out videos for which there is data in the folder already
    videos = filter_channel_or_video(video_ids, videos_path)

    video_detail = service.videos()
    # TODO: Implement this as a function and use it for get_channel_details as well.
    #       The way it's written now would break with >50 channels.
    for i in range(0, len(videos), results):
        sub_list = videos[i:i+results]
        videos_str = ",".join(sub_list)
        request = video_detail.list(
            part=part, id=videos_str, maxResults=results
        )
        try:
            response = request.execute()
            for item in response['items']:
                logger.info(
                    "Attempting to write data for video id {}".format(
                        item['id']
                    )
                )
                # determine if the thumbnail has a person in it
                try:
                    img = item['snippet']['thumbnails']['standard']['url']
                except KeyError:
                    img = item['snippet']['thumbnails']['high']['url']
                    logger.exception(
                        'No standard img url for video id {}'.format(
                            item['id']
                        )
                    )
                has_face = detect_face_v2(img)
                # add has_face and the confidence as keys to the response dict
                item['has_face'] = has_face[0]
                item['detection_confidence'] = None
                if item['has_face']:
                    item['detection_confidence'] = has_face[1][0]['confidence']

                # write the response for the video to a file
                with open(videos_path+'{}.json'.format(item['id']), 'w+') as video_data:
                    response_obj = json.dumps(item)
                    video_data.write(response_obj)
                    logger.info(
                        "Wrote video data for video id {}.".format(
                            item['id']
                        )
                    )
        except HttpError as e:
            logger.exception(
                "The request to the video resource failed. Error {}".format(
                    e.resp
                )
            )
            if e.resp.status == 403:
                break
            else:
                logger.exception(
                    "Failed to get video resource data for videos ids {}".format(
                        videos
                    )
                )
                continue


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

    # write channel detail info
    get_channel_details(service, channels)

    for channel in channels:
        # write channel video data
        get_channel_videos(service, channel)

    # finally, write video details
    get_video_details(service)


if __name__ == "__main__":
    main()
