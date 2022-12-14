"""Read and write grading scales.

A scale file is a simple CSV with no headers. The first column contains the
letter grade, and the second contains the threshold as a decimal number. The
order of the rows matters!

"""

from collections import OrderedDict
import pathlib


def write(path: pathlib.Path, scale):
    """Writes a scale to disk."""
    with path.open("w") as fileobj:
        for letter, threshold in scale.items():
            fileobj.write(f"{letter},{threshold}\n")


def read(path: pathlib.Path):
    """Reads a scale from the file."""
    with path.open() as fileobj:
        lines = fileobj.readlines()

    def parse_line(l):
        letter, threshold = l.split(",")
        threshold = float(threshold)
        return (letter, threshold)

    return OrderedDict(map(parse_line, lines))
