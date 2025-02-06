from recapped import spotify_recapped


def test_is_correct_year_field_missing():
    data = {
        "foo": "bar"
    }

    assert not spotify_recapped.is_correct_year(data, "2025")


def test_is_correct_year():
    data = {
        "ts": "2025-01-01"
    }

    assert not spotify_recapped.is_correct_year(data, "2024")
    assert spotify_recapped.is_correct_year(data, "2025")


def test_is_before_wrapped_cutoff_default():
    data = {
        "ts": "2014-09-09T00:20:27Z"
    }

    assert "2014" not in spotify_recapped.cutoff_dates
    assert data["ts"][5:10] < spotify_recapped.DEFAULT_CUTOFF_DATE
    assert spotify_recapped.is_before_wrapped_cutoff(data)

    data["ts"] = "2014-12-09T00:20:27Z"
    assert data["ts"][5:10] > spotify_recapped.DEFAULT_CUTOFF_DATE
    assert not spotify_recapped.is_before_wrapped_cutoff(data)


def test_is_before_wrapped_cutoff():
    data = {
        "ts": "2024-11-01T00:20:27Z"
    }

    assert "2024" in spotify_recapped.cutoff_dates
    assert data["ts"][5:10] > spotify_recapped.DEFAULT_CUTOFF_DATE
    assert spotify_recapped.is_before_wrapped_cutoff(data)

    data["ts"] = "2024-12-30T00:20:27Z"
    assert not spotify_recapped.is_before_wrapped_cutoff(data)


def test_filter_valid_data():
    data = [
        {  # happy path
            "ts": "2024-11-01T00:20:27Z",
            "master_metadata_track_name": "1",
            "ms_played": 60000
        },
        {  # ms_played < threshold
            "ts": "2024-11-01T00:20:27Z",
            "master_metadata_track_name": "2",
            "ms_played": 10000
        },
        {  # track name is none
            "ts": "2024-11-01T00:20:27Z",
            "master_metadata_track_name": None,
            "ms_played": 60000
        },
        {  # happy path
            "ts": "2024-11-01T00:20:27Z",
            "master_metadata_track_name": "4",
            "ms_played": 60000
        },
        {  # incorrect year
            "ts": "2025-11-01T00:20:27Z",
            "master_metadata_track_name": "5",
            "ms_played": 60000
        },
        {  # not before cutoff date
            "ts": "2024-12-01T00:20:27Z",
            "master_metadata_track_name": "6",
            "ms_played": 60000
        },
        {  # happy path
            "ts": "2024-11-01T00:20:27Z",
            "master_metadata_track_name": "7",
            "ms_played": 60000
        }
    ]

    result = spotify_recapped.filter_valid_data(data, "2024")
    assert len(result) == 3
    assert ["1", "4", "7"] == [d["master_metadata_track_name"] for d in result]
