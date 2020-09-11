import re

import pandas as pd

from .gradebook import Gradebook


def read_egrades_roster(path):
    """Read an eGrades roster CSV into a pandas dataframe.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the CSV file that will be read.

    Returns
    -------
    pandas.DataFrame
        A dataframe indexed by PIDs.

    """
    return pd.read_csv(path, delimiter="\t").set_index("Student ID")


def read_gradescope_gradebook(
    path, standardize_pids=True, standardize_assignments=True
):
    """Read a CSV exported from Gradescope into a Gradebook.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the CSV file that will be read.
    standardize_pids : bool
        Whether to standardize PIDs so that they are all uppercased. This can be
        useful when students who manually join gradescope enter their own PID
        without uppercasing it. Default: True.
    standardize_assignments : bool
        Whether to standardize assignment names so that they are all lowercased.
        Default: True.

    Returns
    -------
    Gradebook

    """
    table = pd.read_csv(path).set_index("SID")

    # drop the total lateness column; it just gets in the way
    table = table.drop(columns="Total Lateness (H:M:S)")

    if standardize_pids:
        table.index = table.index.str.upper()

    # now we create the points table. We use the assumption that the first
    # assignment is in the fifth column (starting_index = 4), and the
    # assignments are in every fourth column thereafter (stride = 4). this
    # assumption is liable to break if gradescope changes their CSV schema.
    starting_index = 4
    stride = 4

    # extract the points
    points = table.iloc[:, starting_index::stride].astype(float)

    if standardize_assignments:
        points.columns = [x.lower() for x in points.columns]

    # the max_points are replicated on every row; we'll just use the first row
    max_points = table.iloc[0, starting_index + 1 :: stride].astype(float)
    max_points.index = points.columns
    max_points.name = "Max Points"

    # the csv contains time since late deadline; we'll booleanize this as
    # simply late or not
    late = (table.iloc[:, starting_index + 3 :: stride] != "00:00:00").astype(bool)
    late.columns = points.columns

    return Gradebook(points, max_points, late, dropped=None)


def _remove_assignment_id(s):
    """Remove the trailing (xxxxx) from a Canvas assignment name."""
    return re.sub(r" +\(\d+\)$", "", s)


def read_canvas_gradebook(
    path,
    standardize_pids=True,
    standardize_assignments=True,
    remove_assignment_ids=True,
):
    """Read a CSV exported from Canvas into a Gradebook.

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
    table = pd.read_csv(path).set_index("SIS User ID")

    # the structure of the table can change quite a bit from quarter to quarter
    # the best approach to extracting the assignments might be to match them using
    # a regex. an assignment is of the form `assignment name (xxxxxx)`, where
    # `xxxxxx` is some integer number.
    def is_assignment(s):
        """Does the string end with parens containing a number?"""
        return bool(re.search(r"\(\d+\)$", s))

    assignments = [c for c in table.columns if is_assignment(c)]

    # keep only the assignments and the student name column, because we'll use
    # the names in a moment to find the max points
    table = table[["Student"] + assignments]

    # the maximum points are stored in a row with student name "Points Possible",
    # and SIS User ID == NaN. For some reason, though, "Points Possible" has a
    # bunch of whitespace at the front... thanks Canvas
    max_points = table[
        pd.isna(table.index) & table["Student"].str.contains("Points Possible")
    ]

    # the result of the above was a dataframe. turn it into a series and get
    # rid of the student index; we don't need it
    max_points = max_points.iloc[0].drop(index="Student").astype(float)
    max_points.name = "Max Points"

    # clean up the table. get rid of the student column, and drop all rows with
    # NaN indices
    points = table[~pd.isna(table.index)].drop(columns=["Student"]).astype(float)

    if standardize_assignments:
        points.columns = points.columns.str.lower()

    if standardize_pids:
        points.index = points.index.str.upper()

    if remove_assignment_ids:
        points.columns = [_remove_assignment_id(c) for c in points.columns]

    # we've possibly changed column names in points table; propagate these
    # changes to max_points
    max_points.index = points.columns

    return Gradebook(points, max_points, late=None, dropped=None)
