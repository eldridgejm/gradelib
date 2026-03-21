"""Read and write grading scales.

A scale file is a simple CSV with no headers. The first column contains the
letter grade, and the second contains the cutoff as a decimal number. The
order of the rows matters!

"""

import pathlib as _pathlib
from collections import OrderedDict
from collections.abc import Mapping


def write(path: str | _pathlib.Path, scale: Mapping):
    """Writes a grading scale to disk.

    Parameters
    ----------
    path : pathlib.Path or str
        The path where the scale will be written.
    scale : Mapping
        A mapping from letter grades to their cutoffs.

    Notes
    -----
    The scale is written as a CSV with no headers. The first column contains the
    letter grade, and the second contains the cutoff as a decimal number.

    """
    path = _pathlib.Path(path)

    with path.open("w") as fileobj:
        for letter, cutoff in scale.items():
            fileobj.write(f"{letter},{cutoff}\n")


def read(path: str | _pathlib.Path) -> OrderedDict:
    """Reads a grading scale from the file.

    Parameters
    ----------
    path : pathlib.Path or str
        The path where the scale is stored.

    Returns
    -------
    OrderedDict
        A mapping from letter grades to their cutoffs.

    """
    path = _pathlib.Path(path)

    with path.open() as fileobj:
        lines = fileobj.readlines()

    def parse_line(line):
        letter, cutoff = line.split(",")
        cutoff = float(cutoff)
        return (letter, cutoff)

    return OrderedDict(map(parse_line, lines))
