from googleapiclient.discovery import build
import os
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
import csv
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

api_key = 'xxxxxxxxxxxxxxxx'
youtube_channel_id = 'xxxxxxxxxxxx'

youtube = build('youtube', 'v3', developerKey=api_key)

def get_video_ids(youtube, channel_id, max_results=50):
    video_ids = []
    next_page_token = None

    while True:
        request = youtube.search().list(
            part="id",
            channelId=channel_id,
            maxResults=max_results,
            pageToken=next_page_token,
            type="video"
        )
        response = request.execute()

        video_ids.extend([item['id']['videoId'] for item in response.get('items', [])])

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    return video_ids

# Fetch the video IDs
video_ids = get_video_ids(youtube, youtube_channel_id)

# Optionally, save to a file
with open('data.txt', 'w') as file:
    for video_id in video_ids:
        file.write(f"{video_id}\n")

print(f"Saved {len(video_ids)} video IDs to channel_video_ids.txt")

#Scraping the transcripts and video details from the video_ids list

def extract_video_description_and_links(video_url):
    try:
        soup = BeautifulSoup(requests.get(video_url).content, 'html.parser')
        pattern = re.compile('(?<=shortDescription":").*(?=","isCrawlable)')
        description = pattern.findall(str(soup))[0].replace('\\n', '\n')

        video_links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', description)

        return description, video_links
    except Exception as e:
        return None, None

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = ' '.join([i['text'] for i in transcript_list])
        return transcript, 'en'  
    except NoTranscriptFound as e:
        try:
            available_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
            for transcript in available_transcripts:
                if transcript.is_generated:
                    transcript_list = transcript.fetch()
                    language = transcript.language_code
                    combined_transcript = ' '.join([i['text'] for i in transcript_list])
                    return combined_transcript, language

            return None, None
        except Exception as e:
 
            return None, None
    except Exception as e:
 
        return None, None

def get_video_details(video_id):
    try:
        yt = YouTube(f'https://www.youtube.com/watch?v={video_id}')
        return {
            'title': yt.title,
            'publish_date': yt.publish_date,
            'video_link': yt.watch_url
        }
    except Exception as e:
 
        return None


video_ids_file = 'data.txt' 
output_csv_file = 'data.csv'


with open(video_ids_file, 'r') as file:
    video_ids = [line.strip() for line in file.readlines()]


with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['video_id', 'title', 'publish_date', 'video_link', 'transcript', 'language', 'description', 'description_links']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    # Process each video ID
    for video_id in video_ids:
        video_details = get_video_details(video_id)
        if video_details:
            transcript, language = get_transcript(video_id)
            description, video_links = extract_video_description_and_links(video_details['video_link'])
            if transcript:
                writer.writerow({
                    'video_id': video_id,
                    'title': video_details['title'],
                    'publish_date': video_details['publish_date'].strftime('%Y-%m-%d') if video_details['publish_date'] else 'N/A',
                    'video_link': video_details['video_link'],
                    'transcript': transcript,
                    'language': language,
                    'description': description,
                    'description_links': ', '.join(video_links) if video_links else 'No links found in description'
                })

print("Processing complete. Details and transcripts (if available) have been saved to the CSV file.")

#Filtering the data to find relevant videos

df = pd.read_csv('channel_video_ids.csv')

# Define the keywords you want to search for
keywords = ['keyword1','keyword2'] 


df['transcript'] = df['transcript'].fillna('').astype(str)
df['description'] = df['description'].fillna('').astype(str)


combined_series = df['transcript'] + " " + df['description']


keyword_mask = combined_series.str.contains('|'.join(keywords), case=False, regex=True)


filtered_df = df[keyword_mask]


filtered_df.to_csv('search_data.csv', index=False)  
