"""Private helper utilities."""

import pandas as pd


def empty_mask_like(table: pd.DataFrame) -> pd.DataFrame:
    """Given a dataframe, create another just like it with every entry False."""
    empty = table.copy()
    empty.iloc[:, :] = False
    return empty.astype(bool)


def in_jupyter_notebook() -> bool:
    """Determine if the code is being run in a Jupyter notebook."""
    try:
        shell = get_ipython().__class__.__name__  # pyright: ignore
        if shell == "ZMQInteractiveShell":
            return True  # Jupyter notebook or qtconsole
        elif shell == "TerminalInteractiveShell":
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False
