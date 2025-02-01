import argparse
import json
import os
import re
from typing import Dict, List, Any, Tuple

listening_threshold = 20000  # in ms
audio_file_pattern = re.compile("^Streaming_History_Audio_(.+)\\.json$")

# TODO: try to figure out a reasonable weighting system based on the other metadata
#       in order to rationalize how Spotify actual orders it's Wrapped
def total_time_played(data: List[Dict[str, Any]]) -> int:
    return sum([d["ms_played"] for d in data])

def top_artists(data: List[Dict[str, Any]], k: int) -> List[str]:
    count_artists = {}
    for d in data:
        # TODO: filter out short played songs earlier
        if d["ms_played"] < listening_threshold:
            continue

        artist_name = d["master_metadata_album_artist_name"]
        if artist_name not in count_artists:
            count_artists[artist_name] = 0
        count_artists[artist_name] += 1
    artists = []
    for (artist, count) in count_artists.items():
        artists.append((artist, count))
    
    artists.sort(key=lambda t: t[1], reverse=True)
    return artists[:k]

def top_songs(data: List[Dict[str, Any]], k: int = 5) -> List[str]:
    count_song_names = {}
    for d in data:
        if d["ms_played"] < listening_threshold:
            continue

        song_name = d["master_metadata_track_name"] 
        artist_name = d["master_metadata_album_artist_name"]

        # TODO: do I need to deduplicate on artist?
        concatenated = song_name + "+" + artist_name
        if concatenated not in count_song_names:
            count_song_names[concatenated] = 0
        count_song_names[concatenated] += 1
    
    song_counts = []
    for (song, count) in count_song_names.items():
        song_counts.append((song, count))
    
    song_counts.sort(key=lambda t: t[1], reverse=True)
    return song_counts[:k] 
    
def read_audio_history(directory: str) -> List[Dict[str, Any]]:
    files =[]
    for (dirpath, _, filenames) in os.walk(directory):
        files.extend([os.path.abspath(os.path.join(dirpath, f)) for f in filenames if audio_file_pattern.match(f) is not None])
    
    result = []
    for file in files:
        with open(file, mode="r", encoding="utf-8") as f:
            result.extend(json.load(f))

    return result

def filter_valid_data(data: List[Dict[str, Any]], year: str) -> List[Dict[str, Any]]:
    return [d for d in data if is_correct_year(d, year) and d["master_metadata_track_name"] is not None and d["ms_played"] > listening_threshold and not d["skipped"]]

def is_correct_year(data: Dict[str, Any], year: str) -> bool:
    if "ts" not in data:
        return False
    return data["ts"].startswith(year)

def main():
    parser = argparse.ArgumentParser("spotify-recapped", description="Analyze your Spotify listening data")
    parser.add_argument("-p", "--path", default="./data", required=False)
    parser.add_argument("-y", "--years", action="append", required=False)
    parser.add_argument("-n", "--num", default=5, required=False)

    args = parser.parse_args()

    data = read_audio_history(args.path)
    data.sort(key=lambda d: d["ts"])

    # determine the years that need to be filtered. if no years are provided, then look at all years
    years = args.years
    if years is None:
        # derive the years so we can bucket the results
        years = list(set([d["ts"][0:4] for d in data]))
    years.sort()

    # data_for_2014 = [d for d in data if is_correct_year(d, "2014")]
    # print(top_songs(data_for_2014))
    # print(top_artists(data_for_2014))

    num = args.num

    # Bucket the data by year
    wrapped_by_year = {}
    for year in years:
        print(f"Analyzing data for {year}")
        filtered_data = filter_valid_data(data, year)
        print(len([d for d in filtered_data if not d["shuffle"]]))

        songs = top_songs(filtered_data, num)  # TODO: parse the song name and artist into a readable format
        artists = top_artists(filtered_data, num)
        time_played = total_time_played(filtered_data) / 1000 / 60
        wrapped_by_year[year] = {
            "songs": songs,
            "artists": artists,
            "time": time_played,
        }
    print(json.dumps(wrapped_by_year, indent=2))


if __name__ == '__main__':
    main()
