"""Private helper utilities."""

import pandas as pd


def empty_mask_like(table: pd.DataFrame) -> pd.DataFrame:
    """Given a dataframe, create another just like it with every entry False."""
    empty = table.copy()
    empty.iloc[:, :] = False
    return empty.astype(bool)
