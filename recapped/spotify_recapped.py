import argparse
import json
import os
import re
from typing import Dict, List, Any, Tuple

DEFAULT_CUTOFF_DATE = "10-31"

encoder = json.JSONEncoder(ensure_ascii=False, indent='\t')  # don't force ASCII in output since the data is unicode
listening_threshold = 25000  # in ms
audio_file_pattern = re.compile("^Streaming_History_Audio_(.+)\\.json$")

cutoff_dates = {
    "2024": "11-12",
    "2023": "11-19",
    "2022": "11-17",
}


def ms_to_minutes(ms: int) -> int:
    return round(ms / 1000 / 60)


def calculate_weight(record: Dict[str, Any]) -> int:
    """
    TODO: unsure if there is an actual weighting algorithm. need to test with more data to be more certain
    """
    weight = 1
    return weight


def total_time_played(data: List[Dict[str, Any]]) -> int:
    return sum([d["ms_played"] for d in data])


def top_artists(data: List[Dict[str, Any]], k: int) -> List[Tuple[str, int, int]]:
    count_artists: Dict[str, Dict[str, int]] = {}  # map artist name to num listens and cumulative time
    for d in data:
        artist_name = d["master_metadata_album_artist_name"]
        if artist_name is not None and artist_name not in count_artists:
            count_artists[artist_name] = {"count": 0, "time": 0}
        temp = count_artists[artist_name]
        temp["count"] += calculate_weight(d)
        temp["time"] += d["ms_played"]
        count_artists[artist_name] = temp
    artists = []
    for (artist, count) in count_artists.items():
        artists.append((artist, count["count"], count["time"]))

    artists.sort(key=lambda t: t[1], reverse=True)
    artists = [(artist, round(count), ms_to_minutes(time)) for (artist, count, time) in artists]
    result = artists[:k]

    if len(result) == 0:
        return []

    # if there is a tie, just include those values
    last_val = result[-1][1]
    for (artist, count, minutes) in artists[k:]:
        if count == last_val:
            result.append((artist, count, minutes))
    return result


def top_songs(data: List[Dict[str, Any]], k: int) -> List[str]:
    count_song_names = {}
    for d in data:
        song_name = d["master_metadata_track_name"]
        artist_name = d["master_metadata_album_artist_name"]

        concatenated = song_name + "+" + artist_name
        if concatenated not in count_song_names:
            count_song_names[concatenated] = 0
        count_song_names[concatenated] += calculate_weight(d)

    song_counts = []
    for (song, count) in count_song_names.items():
        song_counts.append((song, count))

    song_counts.sort(key=lambda t: t[1], reverse=True)
    song_counts = [(song[:song.find("+")], round(count)) for (song, count) in song_counts]
    result = song_counts[:k]

    if len(result) == 0:
        return []

    last_val = result[-1][1]
    for (song, count) in song_counts[k:]:
        if last_val == count:
            result.append((song, count))

    return result


def read_audio_history(directory: str) -> List[Dict[str, Any]]:
    files = []
    for (dirpath, _, filenames) in os.walk(directory):
        files.extend([os.path.abspath(os.path.join(dirpath, f)) for f in filenames if audio_file_pattern.match(f) is not None])

    result = []
    for file in files:
        print(f"Reading listening data from {file}...")
        with open(file, mode="rb") as f:
            result.extend(json.load(f))

    return result


def filter_valid_data(data: List[Dict[str, Any]], year: str) -> List[Dict[str, Any]]:
    current_year_data = [d for d in data
                         if is_correct_year(d, year) and
                         is_before_wrapped_cutoff(d) and
                         d["master_metadata_track_name"] is not None and
                         d["ms_played"] >= listening_threshold]
    return current_year_data


def is_correct_year(data: Dict[str, Any], year: str) -> bool:
    if "ts" not in data:
        return False
    return data["ts"].startswith(year)


def is_before_wrapped_cutoff(data: Dict[str, Any]) -> bool:
    return data["ts"][5:10] < cutoff_dates.get(data["ts"][0:4], DEFAULT_CUTOFF_DATE)


def main():
    parser = argparse.ArgumentParser("spotify-recapped", description="Analyze your Spotify listening data")
    parser.add_argument("-p", "--path", default="./data", required=False)
    parser.add_argument("-y", "--years", action="append", required=False)
    parser.add_argument("-n", "--num", default=5, type=int, required=False)
    parser.add_argument("-a", "--all", default=False, action="store_true", required=False)

    args = parser.parse_args()

    data = read_audio_history(args.path)
    data.sort(key=lambda d: d["ts"])
    data = [d for d in data if d["master_metadata_track_name"] is not None and d["ms_played"] >= listening_threshold]

    # determine the years that need to be filtered. if no years are provided, then look at all years
    years = args.years
    if years is None:
        # derive the years so we can bucket the results
        years = list(set([d["ts"][0:4] for d in data]))
    years.sort()

    num: int = args.num
    is_cumulative: bool = args.all

    if is_cumulative:
        # TODO: handle case where there isn't more than 1 year of data
        print(f"Computing cumulative Spotify Wrapped that spans the years {years[0]}-{years[-1]}")
        # We want to do a calculation on the totality of the data
        songs = top_songs(data, num)
        artists = top_artists(data, num)
        time_played = round(total_time_played(data) / 1000 / 60)
        result = {
            "songs": songs,
            "artists": artists,
            "time": time_played,
        }
        print(encoder.encode(result))
    else:
        # Bucket the data by year
        wrapped_by_year = {}
        for year in years:
            print(f"Analyzing data for {year}")
            filtered_data = filter_valid_data(data, year)

            # TODO: check if the number of results matches the `num` arg, and if not, indicate that
            # TODO: try adding december of previous year to current year for calculations
            songs = top_songs(filtered_data, num)
            artists = top_artists(filtered_data, num)

            if len(songs) != num:
                print(f"There was a tie found, so instead of having {num} songs, found {len(songs)}.")
            if len(artists) != num:
                print(f"There was a tie found, so instead of having {num} artists, found {len(artists)}.")

            time_played = ms_to_minutes(total_time_played(filtered_data))
            wrapped_by_year[year] = {
                "songs": songs,
                "artists": artists,
                "time": time_played,
            }
        print(encoder.encode(wrapped_by_year))


if __name__ == '__main__':
    main()
