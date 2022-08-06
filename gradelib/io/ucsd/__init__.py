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
