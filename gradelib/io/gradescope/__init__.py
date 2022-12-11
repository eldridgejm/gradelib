"""Read grades exported from Gradescope."""

import pandas as pd

from gradelib import Gradebook, Student


def _find_index_of_first_assignment_column(columns):
    # the first column containing an assignment varies depending on whether the
    # gradescope account has been linked with canvas or not. if linked with canvas,
    # there will be an extra column named "section_name" before the assignment columns
    # note that we have set the index to the SID column, so the columns numbers below
    # are one less than appear in the actual .csv. furthermore, sometimes the csv will
    # contain a single "name" column, and other times it will contain a "first name"
    # column as well as a "last name" column.
    #
    # we'll handle these situations by simply searching for the first column name that
    # isn't a header column
    header_columns = {"first name", "last name", "name", "email", "sid", "section_name"}
    for i, column in enumerate(columns):
        if column.lower() not in header_columns:
            return i
    raise ValueError("There is no assignment column.")


def _lateness_in_seconds(lateness):
    """Converts a series of lateness strings in HH:MM:SS format to integer seconds"""
    hours = lateness.str.split(":").str[0].astype(int)
    minutes = lateness.str.split(":").str[1].astype(int)
    seconds = lateness.str.split(":").str[2].astype(int)
    return pd.to_timedelta(3600 * hours + 60 * minutes + seconds, unit="s")


def read(path, standardize_pids=True, standardize_assignments=True):
    """Read a CSV exported from Gradescope into a :class:`gradelib.Gradebook`.

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
    table = pd.read_csv(path, dtype={"SID": str}).set_index("SID")

    if standardize_pids:
        table.index = table.index.str.upper()

    # read the names
    if "First Name" in table:
        student_names = table["First Name"] + " " + table["Last Name"]
    else:
        student_names = table["Name"]

    table.index = [
        Student(pid, name) for (pid, name) in zip(table.index, student_names)
    ]

    # drop the total lateness column; it just gets in the way
    table = table.drop(columns="Total Lateness (H:M:S)")

    # now we read the assignments to create the points table.
    # there are four columns for each assignment: one with the assignment's name
    # a second with the max points for the assignment, a third with the submission
    # time, and a fourth with the lateness.
    stride = 4

    starting_index = _find_index_of_first_assignment_column(table.columns)

    # extract the points
    points_earned = table.iloc[:, starting_index::stride].astype(float)
    points_earned.index = table.index

    if standardize_assignments:
        points_earned.columns = [x.lower() for x in points_earned.columns]

    # the max_points are replicated on every row; we'll just use the first row
    points_possible = table.iloc[0, starting_index + 1 :: stride].astype(float)
    points_possible.index = points_earned.columns
    points_possible.name = "Max Points"

    # the csv contains time since late deadline
    lateness = table.iloc[:, starting_index + 3 :: stride]
    lateness.columns = points_earned.columns
    lateness = lateness.apply(_lateness_in_seconds)  # convert strings to seconds

    return Gradebook(points_earned, points_possible, lateness)
