"""Lyrics dataset collection script.
"""
import argparse
import json
import lyricsgenius
import os
import sys


def get_options():
    """Helper to get CLI options.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-a','--artists', help='Comma separated artist list')
    parser.add_argument('-o','--output', default='./dataset', help='Output directory path')
    parser.add_argument('-v','--genius-verbose', action='store_true', default=True, help='Change genius verbosity')
    parser.add_argument('-n','--genius-max-songs', type=int, help='Maximum number of songs per artist')
    parser.add_argument('-s','--genius-sort', default='popularity', help='Genius song sort order')
    return parser.parse_args()


def cli(opts):

    # Create output directory if necessary.
    if not os.path.exists(opts.output):
        os.mkdir(opts.output)
        print(f'Created output directory: {opts.output}')

    # Create Genius client.
    genius = lyricsgenius.Genius(
        skip_non_songs=True,
        verbose=opts.genius_verbose,
    )

    # Collect list of artists
    if opts.artists:
        artist_list = opts.artists.split(',')
    else:
        artist_list = list(sys.stdin)

    # Iterate over each desired artist.
    for name in artist_list:
        try:
            artist = genius.search_artist(name, sort=opts.genius_sort, max_songs=opts.genius_max_songs)
            for song in artist.songs:
                fname = os.path.join(opts.output, f"{song.id}.json")
                with open(fname, 'w+') as fp:
                    json.dump(song.to_dict(), fp)
        except:
            print(f"An exception occurred when processing artist {name}")


if __name__ == '__main__':
    opts = get_options()
    cli(opts)