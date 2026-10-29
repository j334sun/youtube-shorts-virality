"""YouTube collection helpers adapted from the original research notebook.

Nothing is collected at import time. Call configure_api() explicitly to enable requests.
"""
import os
import random
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd
from googleapiclient.discovery import build

DATA_DIR = Path(__file__).resolve().parents[1] / "data/raw"
WORD_LIST = Path(__file__).resolve().parents[1] / "data/resources/words.txt"
youtube = None


def configure_api():
    global youtube
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("Set YOUTUBE_API_KEY outside this repository before collecting.")
    youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
    return youtube


def _client():
    if youtube is None:
        raise RuntimeError("Call configure_api() explicitly before collecting.")
    return youtube


def _save(frame, filename):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(DATA_DIR / filename, index=False)
    print(f"Saved {len(frame)} rows locally.")
    return frame

# Function that searches for YouTube Shorts based on a query - return the shorts first without attributes
# search first then get the data from the search result
def search_shorts(query, max_results=50):
    # query: string that specifies the search term

    # Random cutoff is a sampling heuristic, not uniform platform sampling.
    days_ago = random.randint(1, 730)
    published_before = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_ago)).isoformat("T") + "Z"

    request = _client().search().list(
        # this is a method from the YT API - creates a request to search for videos
        part="snippet",               # specify the part: this is for metadata
        q=query,         # query string; no Shorts classification is guaranteed
        type="video",                 # ensure only videos are returned
        videoDuration="short",       # API short means less than four minutes; filter durations later.
        maxResults=max_results,      # limits the # of videos returned
        order='date',                # sorts by date
        publishedBefore=published_before,  # returns videos published before the chosen cutoff
        relevanceLanguage='en', # relevance hint, not a strict language filter
        regionCode = 'US', # viewable in the US, not creator location
    )

    return request.execute() # execute the API request


# Get Basic Video data:
# title, description, published date
# channel_id and channel_title
def extract_ids(search_response):
    rows = []
    for item in search_response.get("items", []):
        rows.append({
            'video_id': item['id']['videoId'],
            'channel_id': item['snippet']['channelId']
        })
    return pd.DataFrame(rows, columns=["video_id", "channel_id"])


# Get video stats:
# viewCount, likeCount, commentCount, duration, categoryId
# takes a list of YouTube video_ids and return a dataframe with statistics
def get_video_stats(video_ids):
    stats = []

    for i in range(0, len(video_ids), 50):
        # YouTube only allows max 50 videos per API call
        request = _client().videos().list(
            part="statistics,contentDetails,snippet",
            id=",".join(video_ids[i:i+50])
        )
        response = request.execute()

        for item in response.get("items", []):
            snippet = item["snippet"]
            stats.append({
                "video_id": item["id"],
                "title": snippet.get("title", ""),
                "channel_id": snippet.get("channelId", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "viewCount": item.get("statistics", {}).get("viewCount"),
                "likeCount": item.get("statistics", {}).get("likeCount"),
                "commentCount": item.get("statistics", {}).get("commentCount"),
                "duration": item["contentDetails"].get("duration", "NA"),
                "categoryId": snippet.get("categoryId", None)
            })

    return pd.DataFrame(stats, columns=["video_id", "title", "channel_id", "channel_title", "published_at", "viewCount", "likeCount", "commentCount", "duration", "categoryId"])


def get_channel_stats(channel_ids):
    stats = []
    for i in range(0, len(channel_ids), 50):
        request = _client().channels().list(
            part="snippet,statistics",
            id=",".join(channel_ids[i:i+50])
        )
        response = request.execute()
        for item in response.get("items", []):
            snippet = item["snippet"]
            statistics = item["statistics"]
            stats.append({
                "channel_id": item["id"],
                "channel_created_at": snippet["publishedAt"],
                "subscriberCount": statistics.get("subscriberCount"),
                "videoCount": statistics.get("videoCount")
            })
    return pd.DataFrame(stats, columns=["channel_id", "channel_created_at", "subscriberCount", "videoCount"])


# look at the categories
def get_youtube_categories(region="US"):
    request = _client().videoCategories().list(part="snippet", regionCode=region)
    response = request.execute()
    categories = []
    for item in response['items']:
        if item['snippet']['assignable']:
            categories.append({
                "categoryId": item["id"],
                "categoryName": item["snippet"]["title"]
            })
    return pd.DataFrame(categories)


# 45 keys in total
search_terms_by_category = {
    "Film & Animation": ["tv", "film", "show"],
    "Autos & Vehicles": ["car", "motorcycles", "vehicles"],
    "Music": ["music", "song"],
    "Pets & Animals": ["animals", "pet"],
    "Sports": ["sports", "workout"],
    "Travel & Events": ["travel", "trip"],
    "Gaming": ["gaming", "video games", "gameplay"],
    "People & Blogs": ["vlog", "storytime"],
    "Comedy": ["comedy", "funny", "joke"],
    "Entertainment": ["entertainment", "pop culture", "tv"],
    "News & Politics": ["news", "politics", "interview"],
    "Howto & Style": ["how to", "style", "fashion"],
    "Education": ["education", "learning", "explainer"],
    "Science & Technology": ["science", "technology", "tech"],
    "Nonprofits & Activism": ["activism", "nonprofit", "social cause"]
}


def scrape_by_cate(date, max_results):
    _client()
    all_results = []

    for category, terms in search_terms_by_category.items():
        for term in terms:
            print(f"🔍 Fetching: '{term}' ({category})")

            try:
                # 1. Search
                search_resp = search_shorts(term, max_results=max_results)
                id_df = extract_ids(search_resp)
                if id_df.empty:
                    continue

                # 2. Video stats
                video_df = get_video_stats(id_df['video_id'].tolist())

                # 3. Channel stats
                channel_df = get_channel_stats(id_df['channel_id'].unique().tolist())

                # 4. Merge and tag
                final_df = pd.merge(video_df, channel_df, on='channel_id', how='left')
                final_df["category_name"] = category
                final_df["search_term"] = term
                final_df["collected_at"] = datetime.now(timezone.utc).isoformat()
                all_results.append(final_df)

            except Exception as e:
                print(f"⚠️ Error for '{term}' ({category}): {type(e).__name__}")
                continue

    if not all_results:
        return pd.DataFrame()
    full_df = pd.concat(all_results, ignore_index=True)
    return _save(full_df, f"yt_cate_scrape_{date}.csv")


def scrape_by_random(times, date, max_results):
    _client()
    all_results = []

    # Load the list of common English words from the file
    with WORD_LIST.open(encoding="utf-8") as f:
        word_list = [line.strip() for line in f if line.strip().isalpha()]

    if not word_list:
        raise ValueError("The local word list contains no alphabetic words.")

    for i in range(times):
        random_key = random.choice(word_list)
        print(f"🔍 Fetching: '{random_key}' ({i+1}/{times})")

        try:
            # 1. Search
            search_resp = search_shorts(random_key, max_results=max_results)
            id_df = extract_ids(search_resp)
            if id_df.empty:
                continue

            # 2. Video stats
            video_df = get_video_stats(id_df['video_id'].tolist())

            # 3. Channel stats
            channel_df = get_channel_stats(id_df['channel_id'].unique().tolist())

            # 4. Merge and tag
            final_df = pd.merge(video_df, channel_df, on='channel_id', how='left')
            final_df["random_key"] = random_key
            final_df["collected_at"] = datetime.now(timezone.utc).isoformat()
            all_results.append(final_df)

        except Exception as e:
            print(f"⚠️ Error for '{random_key}': {type(e).__name__}")
            continue

    if all_results:
        full_df = pd.concat(all_results, ignore_index=True)
        _save(full_df, f"yt_rand_scrape_{date}.csv")
        return full_df
    else:
        print("No data collected.")
        return pd.DataFrame()


def scrape_by_term(search_term, times, date, max_results):
    _client()
    all_results = []

    for i in range(times):
        print(f"🔍 Fetching: '{search_term}' ({i+1}/{times})")

        try:
            # 1. Search
            search_resp = search_shorts(search_term, max_results=max_results)
            id_df = extract_ids(search_resp)
            if id_df.empty:
                continue

            # 2. Video stats
            video_df = get_video_stats(id_df['video_id'].tolist())

            # 3. Channel stats
            channel_df = get_channel_stats(id_df['channel_id'].unique().tolist())

            # 4. Merge and tag
            final_df = pd.merge(video_df, channel_df, on='channel_id', how='left')
            final_df["search_term"] = search_term
            final_df["collected_at"] = datetime.now(timezone.utc).isoformat()
            all_results.append(final_df)

        except Exception as e:
            print(f"⚠️ Error during fetch {i+1}: {type(e).__name__}")
            continue

    # Save all
    if all_results:
        full_df = pd.concat(all_results, ignore_index=True)
        slug = re.sub(r"[^A-Za-z0-9_-]+", "_", search_term).strip("_") or "query"
        _save(full_df, f"yt_term_scrape_{slug}_{date}.csv")
        return full_df
    else:
        print("No data collected.")
        return pd.DataFrame()
