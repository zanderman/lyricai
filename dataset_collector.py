"""Lyrics dataset collection script.
"""
import argparse
import csv
import concurrent.futures
import json
import lyricsgenius
import os
import sys
from typing import Iterator, Union


def get_song_lyrics(song: str, artist: str) -> Union[dict,None]:
    """Searches Genius for song details based on song name and artist.

    Args:
        song (str): Title of song
        artist (str): Name of artist

    Returns:
        Union[dict,None]: Song details (from JSON) or `None` if no results.
    """
    genius = lyricsgenius.Genius(
        skip_non_songs=True,
        verbose=False,
    )

    songdetails = genius.search_song(
        title=song,
        artist=artist,
        get_full_info=True,
        )

    if songdetails:
        return songdetails.to_dict()
    else:
        return None


def collect_from_csv(csvfile: str) -> Iterator[dict]:
    """Searches Genius for songs within a CSV file.

    Args:
        csvfile (str):  Path to CSV file.

    Returns:
        Iterator[dict]: Iterator to song dictionary objects with metadata.
    """

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
                future = executor.submit(get_song_lyrics, song=song, artist=artist)
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
    parser.add_argument('-o','--output', default='./dataset', help='Output directory path')
    return parser.parse_args()


def cli(opts):
    """Command-line program function.
    """

    # Determine if CSV file or STDIN.
    if opts.csvfile:
        csvfile = opts.csvfile
    else:
        csvfile = sys.stdin

    for songdict, song, artist in collect_from_csv(csvfile):
        if songdict:
            fname = os.path.join(opts.output, f"{songdict['id']}.json")
            with open(fname, 'w+') as fp:
                json.dump(songdict, fp)
            print(f"[+] \"{song}\", \"{artist}\", \"{songdict['id']}\"", flush=True)
        else:
            print(f"[-] \"{song}\", \"{artist}\"", flush=True)


if __name__ == '__main__':
    opts = get_options()
    cli(opts)