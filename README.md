# YouTube Video Content Analysis

# What
This is a pet project of mine to analyze the various factors involved in the success of a YouTube video. More specifically, I analyze videos in the domains of 
analytics, programming, and software engineering to see what qualities are present in videos that perform relatively well. The analysis includes natural language processing techniques 
like clustering video titles, classification techniques to determine whether or not a person's face is present in the thumbnail, and traditional inferrential statistical methods.

## Results

## Methodology

## Running the code
The first step in getting this code to run is to register an API key with Google's YouTube Data API. Details on how to do this are provided in my [blog post](#), but the 
API is very accessible and the [official documentation](https://developers.google.com/youtube/v3/getting-started) provides plenty of details.
After that, in the terminal, run
```bash
$ pip install -r requirements.txt --no-dependencies

```
The no-dependencies flag is important and ensures that you don't install 2 versions of openCV.

### Notes (mostly for myself)
- Whether or not a person's face is in the video thumbnail cannot be taken at face value; that is to say, a successful YouTube content creator in this space may include 
his or her face in all the thumbnails, which could bias the data. This must be taken into context when performing the analysis.
- Another flaw in this analysis is that it would be difficult to randomly select which content creators to include in the analysis because the YT categorization system 
is not very robust; e.g. most of the content will fall simply under "Education," so I will have to manually decide on which creators are included, and this selection 
is based on YouTubers I watch or know of, which inherintly introduces some selection bias; I don't really address this issue in the analysis, nor am I aware of a 
reasonably time-efficient/resource-efficient way of doing so.
