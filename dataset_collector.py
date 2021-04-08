"""Lyrics dataset collection script.
"""
import argparse
import csv
import concurrent.futures
import json
import lyricsgenius
import os
import sys
from typing import Iterator, Union, List


def get_song_lyrics(genius: lyricsgenius.Genius, song: str, artist: str) -> Union[dict,None]:
    """Searches Genius for song details based on song name and artist.

    Args:
        genius (lyricsgenius.Genius): LyricsGenius object to use for query.
        song (str): Title of song
        artist (str): Name of artist

    Returns:
        Union[dict,None]: Song details (from JSON) or `None` if no results.
    """
    songdetails = genius.search_song(
        title=song,
        artist=artist,
        get_full_info=True,
        )

    if songdetails:
        return songdetails.to_dict()
    else:
        return None


def get_top_songs_for_artist(genius: lyricsgenius.Genius, artist: str, max_songs: int = None) -> List[dict]:
    """Searches Genius for the top songs for a given artist.

    Args:
        genius (lyricsgenius.Genius): LyricsGenius object to use for query.
        artist (str): Name of artist
        max_songs (int, optional): Maximum number of songs to return.

    Returns:
        List[dict]: List of songs or empty if no results.
    """
    artist_obj = genius.search_artist(artist, max_songs=max_songs, sort='popularity')

    if artist_obj:
        return [song.to_dict() for song in artist_obj.songs]
    else:
        return []


def collect_from_artist_csv(csvfile: str, max_songs: int = None) -> Iterator[tuple]:
    """Searches Genius for the top songs for a given artist within a CSV file.

    Args:
        csvfile (str):  Path to CSV file.
        max_songs (int, optional): Maximum number of songs to return.

    Returns:
        Iterator[tuple]: Iterator to song tuple of (song_dict,artist_name).
    """

    # Create music genius.
    genius = lyricsgenius.Genius(
        skip_non_songs=True,
        verbose=False,
        sleep_time=1,
    )

    # Spin-up a threadpool to speed-up the download process.
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_artist = {} # key=future, value=tuple(song,artist,)

        # Read the contents of the song file.
        with open(csvfile, 'r') as fp:

            # Submit each song to the threadpool for download.
            for artist in fp:
                artist = artist.strip() # Remove extra whitespace.
                future = executor.submit(get_top_songs_for_artist, genius=genius, artist=artist, max_songs=max_songs)
                future_to_artist[future] = artist

            # Yield from threadpool as jobs are completed.
            for future in concurrent.futures.as_completed(future_to_artist):
                try:
                    songlist = future.result()
                except Exception as e:
                    print(e, file=sys.stderr)
                    songlist = []
                finally:
                    yield (songlist,future_to_artist[future],)


def collect_from_song_artist_csv(csvfile: str) -> Iterator[tuple]:
    """Searches Genius for songs within a CSV file.

    Args:
        csvfile (str):  Path to CSV file.

    Returns:
        Iterator[tuple]: Iterator to song tuple of (song_dict,song_title,artist_name).
    """

    # Create music genius.
    genius = lyricsgenius.Genius(
        skip_non_songs=True,
        verbose=False,
        sleep_time=1,
    )

    # Spin-up a threadpool to speed-up the download process.
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_songtup = {} # key=future, value=tuple(song,artist,)

        # Read the contents of the song file.
        with open(csvfile, 'r') as fp:
            songreader = csv.reader(fp, delimiter=',', quotechar='"')

            # Submit each song to the threadpool for download.
            for song,artist in songreader:
                song = song.strip()
                artist = artist.split(',')[0].strip() # Only get first artist if a list.
                future = executor.submit(get_song_lyrics, genius=genius, song=song, artist=artist)
                future_to_songtup[future] = (song, artist,)

            # Yield from threadpool as jobs are completed.
            for future in concurrent.futures.as_completed(future_to_songtup):
                try:
                    songdict = future.result()
                except:
                    songdict = None
                finally:
                    yield (songdict,*future_to_songtup[future],)


def get_options():
    """Helper to get CLI options.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('csvfile', help='CSV list of "song,artist"')
    parser.add_argument('--csv-artist', action='store_true', help='CSV contains artist')
    parser.add_argument('-n','--max-songs', type=int, help='Maximum number of songs to search for artist')
    parser.add_argument('--csv-song-artist', action='store_true', help='CSV contains song,artist')
    parser.add_argument('-o','--output', default='./dataset', help='Output directory path')
    return parser.parse_args()


def cli(opts):
    """Command-line program function.
    """

    # Ensure that at least one CSV argument was passed.
    assert opts.csv_artist or opts.csv_song_artist

    # Determine if CSV file or STDIN.
    if opts.csvfile:
        csvfile = opts.csvfile
    else:
        csvfile = sys.stdin

    # Create output directory.
    if not os.path.exists(opts.output):
        os.mkdir(opts.output)

    # CSV file contains song,artist.
    if opts.csv_song_artist:

        for songdict, song, artist in collect_from_song_artist_csv(csvfile):
            if songdict:
                fname = os.path.join(opts.output, f"{songdict['id']}.json")
                with open(fname, 'w') as fp:
                    json.dump(songdict, fp)
                print(f"\"{songdict['id']}\",\"{songdict['title']}\",\"{artist}\"", flush=True)

    # CSV file contains artist only.
    elif opts.csv_artist:

        for songlist, artist in collect_from_artist_csv(csvfile, max_songs=opts.max_songs):
            for songdict in songlist:
                fname = os.path.join(opts.output, f"{songdict['id']}.json")
                with open(fname, 'w') as fp:
                    json.dump(songdict, fp)
                print(f"\"{songdict['id']}\",\"{songdict['title']}\",\"{artist}\"", flush=True)


if __name__ == '__main__':
    opts = get_options()
    cli(opts)