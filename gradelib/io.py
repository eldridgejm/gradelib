import re

import pandas as pd


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


def read_gradescope(path, standardize_pids=True, standardize_assignments=True):
    """Read a CSV exported from Gradescope.

    Warning
    -------

    This is a low-level function which returns a pandas DataFrame. A 
    higher-level convenience function for reading a gradescope CSV directly into
    a :class:`Gradebook` is provided by :meth:`Gradebook.from_gradescope`.

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

    """
    table = pd.read_csv(path, dtype={"SID": str}).set_index("SID")

    # drop the total lateness column; it just gets in the way
    table = table.drop(columns="Total Lateness (H:M:S)")

    if standardize_pids:
        table.index = table.index.str.upper()

    # now we read the assignments to create the points table.
    # there are four columns for each assignment: one with the assignment's name
    # a second with the max points for the assignment, a third with the submission
    # time, and a fourth with the lateness.
    stride = 4

    starting_index = _find_index_of_first_assignment_column(table.columns)

    # extract the points
    points = table.iloc[:, starting_index::stride].astype(float)

    if standardize_assignments:
        points.columns = [x.lower() for x in points.columns]

    # the max_points are replicated on every row; we'll just use the first row
    max_points = table.iloc[0, starting_index + 1 :: stride].astype(float)
    max_points.index = points.columns
    max_points.name = "Max Points"

    # the csv contains time since late deadline
    lateness = table.iloc[:, starting_index + 3 :: stride]
    lateness.columns = points.columns

    return points, max_points, lateness


def _remove_assignment_id(s):
    """Remove the trailing (xxxxx) from a Canvas assignment name."""
    return re.sub(r" +\(\d+\)$", "", s)


def read_canvas(
    path,
    *,
    standardize_pids=True,
    standardize_assignments=True,
    remove_assignment_ids=True,
):
    """Read a CSV exported from Canvas.

    Warning
    -------

    This is a low-level function which returns a pandas DataFrame. A 
    higher-level convenience function for reading a canvas CSV directly into
    a :class:`Gradebook` is provided by :meth:`Gradebook.from_canvas`.

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
    points : pd.DataFrame
        Points table, one row per student.
    maximums : pd.Series
        Maximum points for each assignment.

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

    return points, max_points


def write_canvas_grades(existing, output, grades):
    """Export new assignments to a Canvas-compatible CSV.

    This is mostly useful for uploading computed summary grades to Canvas,
    such as the overall homework score, etc. It will create a CSV that can be
    uploaded directly to gradescope in order to create new assignments.

    Parameters
    ----------
    existing : str
        Path to an existing canvas CSV.
    output : str
        Path where the output will be written.
    grades : pd.DataFrame
        A dataframe, indexed by student PIDS, where each column is an assignment
        that will be uploaded to canvas.

    """
    table = pd.read_csv(existing)

    # the part of the table that is required, and nothing more. includes
    # student name, ID, etc.
    required_part = table.iloc[:, :5]

    full_table = required_part.merge(
        grades, left_on="SIS User ID", right_index=True, how="left"
    )
    full_table.to_csv(output, index=False)


def write_egrades(existing, output, letters):
    """Export egrades to csv.

    Students who have elected to take the class on a P/NP basis will
    automatically have their letter grade converted to P or NP, as appropriate.

    Parameters
    ----------
    existing : str
        Path to an existing egrades roster CSV.
    output : str
        Path where the output will be written.
    letters : pd.Series
        The letter grades, indexed by PID.

    """
    letters = letters.copy()
    roster = pd.read_csv(existing, delimiter="\t")
    original_columns = roster.columns
    roster = roster.set_index("Student ID")

    if set(letters.index) != set(roster.index):
        raise ValueError("Mismatched indices.")

    roster["Final_Assigned_Egrade"] = letters

    # set grades for P/NP option
    pnp = roster["Grade Option"] == "P"

    def is_passing(letter):
        return letter[0] in {"A", "B", "C"}

    is_passing = roster["Final_Assigned_Egrade"].apply(is_passing)

    roster.loc[pnp & is_passing, "Final_Assigned_Egrade"] = "P"
    roster.loc[pnp & ~is_passing, "Final_Assigned_Egrade"] = "NP"

    roster = roster.reset_index()[original_columns]
    roster.to_csv(output, index=False)
