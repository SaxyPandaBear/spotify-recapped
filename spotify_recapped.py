import argparse
import json
import os
import re
from typing import Dict, List, Any, Tuple

encoder = json.JSONEncoder(ensure_ascii=False, indent='\t')  # don't force ASCII in output since the data is unicode
listening_threshold = 25000  # in ms
audio_file_pattern = re.compile("^Streaming_History_Audio_(.+)\\.json$")

cutoff_dates = {
    "2024": "11-12",
    "2023": "11-19",
}

# TODO: try to figure out a reasonable weighting system based on the other metadata
#       in order to rationalize how Spotify actual orders it's Wrapped. It's possible
#       that the weight system incorporates the amount of time a song is listened to,
#       but ignore that for now
def calculate_weight(record: Dict[str, Any]) -> int:
    weight = 1

    # use a precedence system?
    # if record["reason_start"] == "clickrow":
    #     weight = 1
    # if record["reason_start"] == "trackdone":
    #     weight = 0.95
    # if record["shuffle"]:
    #     weight = 0.9
    # if record["ms_played"] < listening_threshold:
    #     weight = 0.3
    # if record["skipped"]:
    #     weight = 0.2

    return weight

def total_time_played(data: List[Dict[str, Any]]) -> int:
    return sum([d["ms_played"] for d in data])

def top_artists(data: List[Dict[str, Any]], k: int) -> List[str]:
    count_artists = {}
    for d in data:
        artist_name = d["master_metadata_album_artist_name"]
        if artist_name not in count_artists:
            count_artists[artist_name] = 0
        count_artists[artist_name] += calculate_weight(d)
    artists = []
    for (artist, count) in count_artists.items():
        artists.append((artist, count))
    
    artists.sort(key=lambda t: t[1], reverse=True)
    artists = [(artist, round(count)) for (artist, count) in artists]
    return artists[:k]

def top_songs(data: List[Dict[str, Any]], k: int = 5) -> List[str]:
    count_song_names = {}
    for d in data:
        song_name = d["master_metadata_track_name"] 
        artist_name = d["master_metadata_album_artist_name"]

        # TODO: do I need to deduplicate on artist?
        concatenated = song_name + "+" + artist_name
        if concatenated not in count_song_names:
            count_song_names[concatenated] = 0
        count_song_names[concatenated] += calculate_weight(d)
    
    song_counts = []
    for (song, count) in count_song_names.items():
        song_counts.append((song, count))
    
    song_counts.sort(key=lambda t: t[1], reverse=True)
    result = []
    for (song, count) in song_counts[:k]:
        # strip out the song name from the first arg
        song_name = song[:song.find("+")]
        result.append((song_name, round(count)))
    return result
    
def read_audio_history(directory: str) -> List[Dict[str, Any]]:
    files =[]
    for (dirpath, _, filenames) in os.walk(directory):
        files.extend([os.path.abspath(os.path.join(dirpath, f)) for f in filenames if audio_file_pattern.match(f) is not None])
    
    result = []
    for file in files:
        print(f"Reading listening data from {file}...")
        with open(file, mode="rb") as f:
            result.extend(json.load(f))

    return result

def filter_valid_data(data: List[Dict[str, Any]], year: str) -> List[Dict[str, Any]]:
    return [d for d in data 
        if is_correct_year(d, year) and 
        is_before_wrapped_cutoff(d) and 
        d["master_metadata_track_name"] is not None 
        and d["ms_played"] >= listening_threshold
    ]

def is_correct_year(data: Dict[str, Any], year: str) -> bool:
    if "ts" not in data:
        return False
    return data["ts"].startswith(year)

# TODO: will each year have a different cutoff date?
def is_before_wrapped_cutoff(data: Dict[str, Any]) -> bool:
    return data["ts"][5:10] < cutoff_dates.get(data["ts"][0:4], "10-31")

def main():
    parser = argparse.ArgumentParser("spotify-recapped", description="Analyze your Spotify listening data")
    parser.add_argument("-p", "--path", default="./data", required=False)
    parser.add_argument("-y", "--years", action="append", required=False)
    parser.add_argument("-n", "--num", default=5, type=int, required=False)

    args = parser.parse_args()

    data = read_audio_history(args.path)
    data.sort(key=lambda d: d["ts"])

    # determine the years that need to be filtered. if no years are provided, then look at all years
    years = args.years
    if years is None:
        # derive the years so we can bucket the results
        years = list(set([d["ts"][0:4] for d in data]))
    years.sort()

    num = args.num

    # Bucket the data by year
    wrapped_by_year = {}
    for year in years:
        print(f"Analyzing data for {year}")
        filtered_data = filter_valid_data(data, year)

        songs = top_songs(filtered_data, num)  # TODO: parse the song name and artist into a readable format
        artists = top_artists(filtered_data, num)
        time_played = round(total_time_played(filtered_data) / 1000 / 60)
        wrapped_by_year[year] = {
            "songs": songs,
            "artists": artists,
            "time": time_played,
        }
    print(encoder.encode(wrapped_by_year))


if __name__ == '__main__':
    main()
