# Organization
data\
├── channels\
└── videos\
    ├── data\
        ├── unit_channel\
        └── unit_video\
    └── thumbnails

## data/channels
This folder contains JSON files of channel data 
written from the get_channel_details func in collector.py. This function makes use of 
the [channels resource](https://developers.google.com/youtube/v3/docs/channels) of the 
YouTube Data API. It gets data from the following resource properties:
- snippet
- statistics
- brandingSettings

## data/videos/data/unit_channel
Channel-level data on YouTube videos. Each file has some info on the videos published by the channel, including 
how many videos the channel has, and data on each of the videos in the 'items' list of the JSON object.
This data comes from the get_channel_videos func in collector.py, which utilizes the [search resource](https://developers.google.com/youtube/v3/docs/search) of the 
YouTube Data API.

## data/videos/data/unit_video
Video-level data (each file name is the corresponding video identifier). Utilizes the [videos resource](https://developers.google.com/youtube/v3/docs/videos).

## data/videos/thumbnails
Downloaded thumbnail images of all the videos.