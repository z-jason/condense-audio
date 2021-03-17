"""
Store a collection of NamedTuple
"""

from trim_movie.timestamp import Timestamp
from typing import NamedTuple


class InputFiles(NamedTuple):
    video_path: str
    subtitle_path: str


class IntermediateOutfile(NamedTuple):
    path: str
    duration: Timestamp


class OutputFiles(NamedTuple):
    audio_path: str
    subtitle_path: str


class Configuration(NamedTuple):
    print_subtitle: bool
    tmpdir: str