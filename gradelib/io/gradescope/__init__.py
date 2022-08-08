import pandas as pd

from gradelib import MutableGradebook, Student


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
    """Read a CSV exported from Gradescope.

    Warning
    -------

    This is a low-level function which returns a pandas DataFrame. A
    higher-level convenience function for reading a gradescope CSV directly into
    a :class:`MutableGradebook` is provided by :meth:`Gradebook.from_gradescope`.

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
    points : pd.DataFrame
        Points table, one row per student.
    maximums : pd.Series
        Maximum points for each assignment.
    lateness : pd.DataFrame
        The lateness of each submission, as a string.

        Read a gradescope CSV into a gradebook.

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

    """
    table = pd.read_csv(path, dtype={"SID": str}).set_index("SID")

    if standardize_pids:
        table.index = table.index.str.upper()

    # read the names
    student_names = table["First Name"] + " " + table["Last Name"]
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
    points_marked = table.iloc[:, starting_index::stride].astype(float)
    points_marked.index = table.index

    if standardize_assignments:
        points_marked.columns = [x.lower() for x in points_marked.columns]

    # the max_points are replicated on every row; we'll just use the first row
    points_possible = table.iloc[0, starting_index + 1 :: stride].astype(float)
    points_possible.index = points_marked.columns
    points_possible.name = "Max Points"

    # the csv contains time since late deadline
    lateness = table.iloc[:, starting_index + 3 :: stride]
    lateness.columns = points_marked.columns
    lateness = lateness.apply(_lateness_in_seconds)  # convert strings to seconds

    return MutableGradebook(points_marked, points_possible, lateness)
