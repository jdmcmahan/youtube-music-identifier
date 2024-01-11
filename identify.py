#!/usr/bin/env python3

import os
import sys
import argparse
import json
import re
import pathlib
import datetime
import shutil

from collections import namedtuple
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from rapidfuzz.distance import Levenshtein

COLOR_GOOD = '\u001B[32m'
COLOR_WARN = '\u001B[33m'
COLOR_BAD = '\u001B[31m'
COLOR_RESET = '\u001B[0m'

def deserialize_metadata(path):
    Metadata = namedtuple('Metadata', 'id album artist duration href is_liked title')

    file = open(path)
    try:
        return list(map(lambda element: Metadata(**element), json.load(file)))
    finally:
        file.close()

def normalize_name(name):
    return re.sub(r"[\'\"\?\&\*\:\/]", '_', name)

def enumerate_distances(name, metadata):
    distances = {}
    for element in metadata:
        normalized = normalize_name(element.title)

        distance = Levenshtein.distance(normalized, name)
        distances.setdefault(distance, []).append(element)

    return distances

def get_song_duration(path):
    audio_format = path.suffix
    if audio_format.casefold() == '.mp3':
        audio = MP3(path)
        return datetime.timedelta(seconds=audio.info.length)
    elif audio_format.casefold() == '.flac':
        audio = FLAC(path)
        return datetime.timedelta(seconds=audio.info.length)

    raise SystemError(f'Unknown audio format {audio_format} for file {path}')

def disambiguate(path, distances):
    MetadataScore = namedtuple('MetadataScore', 'distance metadata')

    choices = []
    # this could probably be ~fawncier~ with something like itertools.chain.from_iterable
    for key in sorted(distances.keys()):
        for value in distances[key]:
            choices.append(MetadataScore(key, value))

    duration = get_song_duration(path)
    limit = 5

    while True:
        print(f'Choose metadata for file {path.name} (duration {duration})')

        curated = choices[:limit]
        for i, option in enumerate(curated):
            title_color = COLOR_BAD
            if option.distance <= 3:
                title_color = COLOR_GOOD
            elif option.distance <= 10:
                title_color = COLOR_WARN

            raw_time = datetime.datetime.strptime(option.metadata.duration, '%M:%S')
            target_duration = datetime.timedelta(hours=raw_time.hour, minutes=raw_time.minute, seconds=raw_time.second)

            duration_color = COLOR_BAD
            if duration == target_duration:
                duration_color = COLOR_GOOD
            elif abs(duration.seconds - target_duration.seconds) <= 1:
                duration_color = COLOR_WARN

            print(f'  [{i + 1}] {option.metadata.title} by {option.metadata.artist} ({title_color}distance = {option.distance}{COLOR_RESET}, {duration_color}duration = {option.metadata.duration}{COLOR_RESET})')

        choice = input("[m]ore, [s]kip: ")
        if choice.casefold() == 'm':
            limit += 5
            continue
        elif choice.casefold() == 's':
            return None
        elif choice.isnumeric():
            index = int(choice) - 1
            if 0 <= index < len(curated):
                return curated[index].metadata.id

        print(f'{choice} is not a valid option!')

def determine_id(path, metadata):
    distances = enumerate_distances(path.stem, metadata)

    if 0 in distances.keys() and len(distances[0]) == 1:
        return distances[0][0].id

    return disambiguate(path, distances)

def main():
    parser = argparse.ArgumentParser(description='Identify unstructured song files')

    parser.add_argument('metadata', help='the YouTube Music metadata file in JSON format')

    parser.add_argument('-d', '--dir', help='the input directory containing music files to identify', default=os.getcwd())
    parser.add_argument('-o', '--output-dir', help='the output directory', default=os.getcwd())
    parser.add_argument('--copy', help='copy files instead of moving/renaming them', action='store_true')

    args = parser.parse_args()

    metadata = deserialize_metadata(args.metadata)

    input_dir = args.dir
    output_dir = args.output_dir
    copy = args.copy

    for filename in os.listdir(input_dir):
        path = pathlib.Path(input_dir, filename).resolve()
        extension = path.suffix

        if path.is_dir() or extension.casefold() not in ['.mp3', '.flac']:
            continue

        target_id = determine_id(path, metadata)
        if not target_id:
            continue

        target_path = pathlib.Path(output_dir, target_id + extension).resolve()

        os.makedirs(output_dir, exist_ok=True)
        if copy:
            print(f'Copying {path.name} to {target_path}')
            shutil.copy2(path, target_path)
        else:
            print(f'Moving {path.name} to {target_path}')
            shutil.move(path, target_path)

if __name__ == "__main__":
    sys.exit(main())
