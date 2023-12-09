"""Read Canvas gradebooks."""

import re as _re
import pathlib as _pathlib
from typing import Union


import pandas as _pd
import numpy as _np

from gradelib import Gradebook, Student


def _remove_assignment_id(s: str) -> str:
    """Remove the trailing (xxxxx) from a Canvas assignment name."""
    return _re.sub(r" +\(\d+\)$", "", s)


def read(
    path: Union[str, _pathlib.Path],
    *,
    standardize_pids=True,
    standardize_assignments=True,
    remove_assignment_ids=True,
) -> Gradebook:
    """Read a CSV of grades exported from Canvas.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the CSV file that will be read.
    standardize_pids : bool
        Whether to standardize PIDs so that they are all uppercased. Default:
        True.
    standardize_assignments : bool
        Whether to standardize assignment names so that they are all lowercased.
        Default: True
    remove_assignment_ids : bool
        Whether to remove the unique ID code that Canvas appends to each
        assignment name.  Default: True.

    Returns
    -------
    Gradebook

    """
    table = _pd.read_csv(path).set_index("SIS User ID")

    if standardize_pids:
        table.index = table.index.str.upper()

    # read the names
    student_names = table["Student"]

    def _student(pid, name):
        # some of the pids are nan; we will preserve these
        if _pd.isna(pid):
            return _np.nan
        else:
            return Student(pid, name)

    table.index = [
        _student(pid, name) for (pid, name) in zip(table.index, student_names)
    ]

    # the structure of the table can change quite a bit from quarter to quarter
    # the best approach to extracting the assignments might be to match them using
    # a regex. an assignment is of the form `assignment name (xxxxxx)`, where
    # `xxxxxx` is some integer number.
    def is_assignment(s):
        """Does the string end with parens containing a number?"""
        return bool(_re.search(r"\(\d+\)$", s))

    assignments = [c for c in table.columns if is_assignment(c)]

    # keep only the assignments and the student name column, because we'll use
    # the names in a moment to find the max points
    table = table.loc[:, ["Student"] + assignments]

    # the maximum points are stored in a row with student name "Points Possible",
    # and SIS User ID == NaN. For some reason, though, "Points Possible" has a
    # bunch of whitespace at the front... thanks Canvas
    points_possible = table[
        _pd.isna(table.index) & table["Student"].str.contains("Points Possible")
    ]

    # the result of the above was a dataframe. turn it into a series and get
    # rid of the student index; we don't need it
    points_possible = points_possible.iloc[0].drop(index="Student").astype(float)
    points_possible.name = "Max Points"

    # clean up the table. get rid of the student column, and drop all rows with
    # NaN indices
    points_earned = (
        table[~_pd.isna(table.index)].drop(columns=["Student"]).astype(float)
    )

    if standardize_assignments:
        points_earned.columns = points_earned.columns.str.lower()

    if remove_assignment_ids:
        points_earned.columns = [
            _remove_assignment_id(c) for c in points_earned.columns
        ]

    # we've possibly changed column names in points table; propagate these
    # changes to max_points
    points_possible.index = points_earned.columns

    return Gradebook(points_earned, points_possible)
