#!/usr/bin/python
# -*- coding: utf-8 -*-

from glob import glob
from subprocess import *
from trim_movie.subtitle import Caption, AnyCaption
from trim_movie.type import *
from trim_movie import condenser
from trim_movie.logger import log
from trim_movie.args_helper import get_subtitle_outfile, get_audio_outfile
from typing import List


import argparse
import ass
import os
import re
import webvtt


def get_files(patterns: List[str]) -> List[str]:
    file_matches = []
    for pattern in patterns:
        file_matches += glob(pattern)
    return file_matches


def folder_exists(folder: str) -> str:
    assert os.path.isdir(folder), "Folder %s not found" % folder
    return folder


def main() -> int:
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument(
        '--vin', required=True,
        dest='video_in', help='Video infile')
    parser.add_argument('--out', help='Outfile')
    parser.add_argument(
        '--sin', dest='sub_in',
        help='Subtitle infile. If not present, infer from `video_in`. For example, if `video_in` is /path/to/foo.mp4, then this field will be /path/to/foo.vtt')
    parser.add_argument('--sout', dest='sub_out', help='Subtitle outfile.')
    parser.add_argument('--tmpdir', default="/tmp/lingq", type=folder_exists)
    parser.add_argument('--keep-tmpdir', default=False, action='store_true')
    parser.add_argument(
        '--print-subtitle',
        default=False,
        action='store_true',
        help='If true, only print filtered / processed subtitle w/o processing the video')
    parser.add_argument(
        '--video-idx-regex',
        # regex = ".*(S\d+E\d+)"
        default=".*( \\b\d{2}\\b )\(",
        help="A regex pattern to match video input's index")

    args = parser.parse_args()

    video_infile = os.path.abspath(args.video_in)
    configuration = Configuration(
        args.print_subtitle,
        os.path.join(args.tmpdir, "list.txt"),
        args.tmpdir,
        args.keep_tmpdir,
        "flac")  # TODO: Hardcoded
    regex = args.video_idx_regex

    match = re.match(regex, video_infile)

    if args.sub_in:
        subtitle_infile = os.path.abspath(args.sub_in)
    else:
        # Infer from `video_infile`
        # For example, `video_infile` = "雙層公寓：東京 2019-2020_S01E01_重返東京.mp4"
        #                                                       ******
        #  we will try to find subtitle in the same directory matching `*S01E01*.vtt`
        # TODO: Extract to a helper method (video_infile -> subtitle_infile)
        match = re.match(regex, video_infile)
        assert match is not None, "Did not specify `--sin`. Can't infer from `--vin` either."
        pattern = match.group(1)
        file_matches = get_files([
            os.path.join(os.path.dirname(video_infile),
                         "*{pattern}*.vtt".format(pattern=pattern)),
            os.path.join(os.path.dirname(video_infile),
                         "*{pattern}*.ass".format(pattern=pattern))
        ])
        if len(file_matches) != 1:
            import json
            log(
                f"[ERROR] len(file_matches) != 1. pattern = {repr(pattern)}. file_matches is\n {json.dumps(file_matches, indent=4)}")
            import sys
            sys.exit(1)
        subtitle_infile = file_matches[0]

    subtitle_outfile = get_subtitle_outfile(args.sub_out, match, video_infile)
    final_outfile = get_audio_outfile(args.out, match, video_infile)

    final_outfile_dir = os.path.dirname(final_outfile)

    assert os.path.isfile(video_infile), "File %s not found" % subtitle_infile
    assert os.path.isfile(
        subtitle_infile), "File %s not found" % subtitle_infile

    # Make sure the dir for outfile exists
    if not os.path.exists(final_outfile_dir):
        os.makedirs(final_outfile_dir)

    print("Running with the following parameters:\n" +
          'Input\n' +
          '  Video = "%s"\n' % video_infile +
          '  Sub = "%s"\n' % subtitle_infile +
          'Output\n' +
          '  Audio = "%s"\n' % final_outfile +
          '  Sub = "%s"\n' % subtitle_outfile)

    audioCondenser: condenser.AudioCondenser = condenser.Builder()\
        .setInputFiles(InputFiles(video_infile, subtitle_infile))\
        .setOutputFiles(OutputFiles(final_outfile, subtitle_outfile))\
        .setConfiguration(configuration)\
        .setIsValidSubtitleFunc(is_valid_subtitle)\
        .setMapSubtitleFunc(map_subtile)\
        .build()

    with audioCondenser as c:
        c.run()

    return 0

# TODO: Provide these function via extension
def is_valid_subtitle(filename: str, caption: AnyCaption) -> bool:
    if isinstance(caption, webvtt.Caption):
        if '♪' in caption.text:
            return False
        if (len(caption.end) != len(caption.start)):
            raise ValueError(
                "Caption start & end doesn't have the same len: %s" % str(caption))
        if (caption.end < caption.start):
            raise ValueError("Caption end < caption start: %s" % str(caption))
        return True
    elif isinstance(caption, ass.line.Dialogue):
        if caption.text is None or caption.text.strip() == "":
            return False
        if caption.name == 'NTP':
            return False
        # TODO: Hardcoded - won't work for another *.ass file
        return caption.style != '*Default'
    elif isinstance(caption, ass.line.Comment):
        return False
    else:
        raise ValueError(
            f"Invalid subtitle type {type(caption)} for file {repr(filename)}")


def map_subtile(caption: Caption) -> Caption:
    new_text = re.sub("\(.+\)", "", caption.text)
    if new_text == caption.text:
        return caption
    return Caption(caption.start, caption.end, new_text)


if __name__ == '__main__':
    main()
