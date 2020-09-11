"""A package for computing overall grades in courses @ UCSD."""

import collections.abc
import re
import itertools

import numpy as np
import pandas as pd


class Error(Exception):
    """Generic error."""


class Assignments(collections.abc.Collection):
    """A collection of assignments."""

    def __init__(self, names):
        self._names = list(names)

    def __contains__(self, element):
        return element in self._names

    def __len__(self):
        return len(self._names)

    def __iter__(self):
        return iter(self._names)

    def starting_with(self, prefix):
        """Return only assignments starting with the prefix."""
        return self.__class__(x for x in self._names if x.startswith(prefix))

    def containing(self, substring):
        """Return only assignments containing the substring."""
        return self.__class__(x for x in self._names if substring in x)

    def __repr__(self):
        return f"Assignments(names={self._names})"

    def __add__(self, other):
        return Assignments(set(self._names + other._names))

    def __getitem__(self, index):
        return self._names[index]


def read_egrades_roster(path):
    """Read an eGrades roster CSV into a pandas dataframe."""
    return pd.read_csv(path, delimiter="\t").set_index("Student ID")


def read_gradescope_gradebook(path, normalize_pids=True, normalize_assignments=True):
    """Read a CSV exported from Gradescope into a Gradebook.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the CSV file that will be read.
    normalize_pids : bool
        Whether to normalize PIDs so that they are all uppercased. This is useful
        since students who manually join gradescope might enter their own PID,
        and may not uppercase it. Default: True.
    normalize_assignments : bool
        Whether to normalize assignment names so that they are all lowercased.
        Default: True.

    Returns
    -------
    Gradebook

    """
    table = pd.read_csv(path).set_index("SID")

    # drop the total lateness column; it just gets in the way
    table = table.drop(columns="Total Lateness (H:M:S)")

    if normalize_pids:
        table.index = table.index.str.upper()

    # now we create the points table. We use the assumption that the first
    # assignment is in the fifth column (starting_index = 4), and the
    # assignments are in every fourth column thereafter (stride = 4). this
    # assumption is liable to break if gradescope changes their CSV schema.
    starting_index = 4
    stride = 4

    # extract the points
    points = table.iloc[:, starting_index::stride].astype(float)

    if normalize_assignments:
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
    path, normalize_pids=True, normalize_assignments=True, remove_assignment_ids=True
):
    """Read a CSV exported from Canvas into a Gradebook.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the CSV file that will be read.
    normalize_pids : bool
        Whether to normalize PIDs so that they are all uppercased. This is
        useful since students who manually join gradescope might enter their
        own PID, and may not uppercase it. Default: True.
    normalize_assignments : bool
        Whether to normalize assignment names so that they are all lowercased.
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

    # clean up the table. get rid of the student column, and drop all rows with
    # NaN indices
    points = table[~pd.isna(table.index)].drop(columns=["Student"]).astype(float)

    if normalize_assignments:
        points.columns = points.columns.str.lower()

    if normalize_pids:
        points.index = points.index.str.upper()

    if remove_assignment_ids:
        points.columns = [_remove_assignment_id(c) for c in points.columns]

    # we've possibly changed column names in points table; propagate these
    # changes to max_points
    max_points.index = points.columns

    return Gradebook(points, max_points, late=None, dropped=None)


def _empty_mask_like(table):
    """Given a dataframe, create another just like it with every entry False."""
    empty = table.copy()
    empty.iloc[:, :] = False
    return empty.astype(bool)


class Gradebook:
    """A collection of grades."""

    def __init__(self, points, maximums, late=None, dropped=None):
        self.points = points
        self.maximums = maximums
        self.late = late if late is not None else _empty_mask_like(points)
        self.dropped = dropped if dropped is not None else _empty_mask_like(points)

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} object with "
            f"{len(self.assignments)} assignments "
            f"and {len(self.pids)} students>"
        )

    @classmethod
    def combine(cls, gradebooks, restrict_pids=None):
        """Create a gradebook by safely combining several existing gradebooks.

        It is crucial that the combined gradebooks have exactly the same
        students -- we don't want students to be missing grades. This function
        checks to make sure that the gradebooks have the same students before
        combining them. Similarly, it verifies that each gradebook has different
        assignments.

        Parameters
        ----------
        gradebooks : Collection[Gradebook]
            The gradebooks to combine. Must have matching indices and unique
            column names.
        restrict_pids : Collection[str] or None
            If provided, each input gradebook will be restricted to the PIDs
            given before attempting to combine them. This is a convenience
            option, and it simply calls Gradebook.restrict_pids on each of the
            inputs.  Default: None

        Returns
        -------
        Gradebook
            A gradebook combining all of the input gradebooks.

        Raises
        ------
        ValueError
            If the PID indices of gradebooks do not match, or if there is a
            duplicate assignment name.

        """
        gradebooks = list(gradebooks)

        if restrict_pids is not None:
            gradebooks = [g.restrict_pids(restrict_pids) for g in gradebooks]

        # check that all gradebooks have the same PIDs
        reference_pids = gradebooks[0].pids
        for gradebook in gradebooks[1:]:
            if gradebook.pids != reference_pids:
                raise ValueError("Not all gradebooks have the same PIDs.")

        # check that all gradebooks have different assignment names
        number_of_assignments = sum(len(g.assignments) for g in gradebooks)
        unique_assignments = set()
        for gradebook in gradebooks:
            unique_assignments.update(gradebook.assignments)

        if len(unique_assignments) != number_of_assignments:
            raise ValueError("Gradebooks have duplicate assignments.")

        # create the combined notebook
        def concat_attr(a):
            """Create a DF/Series by combining the same attribute across gradebooks."""
            all_tables = [getattr(g, a) for g in gradebooks]
            return pd.concat(all_tables, axis=1)

        points = concat_attr("points")
        maximums = concat_attr("maximums")
        late = concat_attr("late")
        dropped = concat_attr("dropped")

        return cls(points, maximums, late, dropped)

    @property
    def assignments(self):
        return Assignments(self.points.columns)

    @property
    def pids(self):
        return set(self.points.index)

    def restrict_pids(self, to):
        """Restrict the gradebook to only the supplied PIDS.

        Parameters
        ----------
        to : Collection[str]
            A collection of PIDs. For instance, from the final course roster.

        Returns
        -------
        Gradebook
            A Gradebook with only these PIDs.

        Raises
        ------
        KeyError
            If a PID was specified that is not in the gradebook.

        """
        pids = list(to)
        extras = set(pids) - set(self.pids)
        if extras:
            raise KeyError(f"These PIDs were not in the gradebook: {extras}.")

        r_points = self.points.loc[pids].copy()
        r_late = self.late.loc[pids].copy()
        r_dropped = self.dropped.loc[pids].copy()
        return self.__class__(r_points, self.maximums, r_late, r_dropped)

    def restrict_assignments(self, to):
        """Restrict the gradebook to only the supplied assignments.

        Parameters
        ----------
        to : Collection[str]
            A collection of assignment names.

        Returns
        -------
        Gradebook
            A Gradebook with only these assignments.

        Raises
        ------
        KeyError
            If an assignment was specified that was not in the gradebook.

        """
        assignments = list(to)
        extras = set(assignments) - set(self.assignments)
        if extras:
            raise KeyError(f"These assignments were not in the gradebook: {extras}.")

        r_points = self.points.loc[:, assignments].copy()
        r_maximums = self.maximums[assignments].copy()
        r_late = self.late.loc[:, assignments].copy()
        r_dropped = self.dropped.loc[:, assignments].copy()
        return self.__class__(r_points, r_maximums, r_late, r_dropped)

    def number_of_lates(self, within=None):
        """Return the number of late assignments for each student as a Series.

        Parameters
        ----------
        within : Collection[str]
            A collection of assignment names that will be used to restrict the
            gradebook. If None, all assignments will be used. Default: None

        Returns
        -------
        pd.Series
            A series mapping PID to number of late assignments.

        Raises
        ------
        ValueError
            If `within` is empty.

        """
        if within is None:
            within = self.assignments
        else:
            within = list(within)

        if not within:
            raise ValueError("Cannot pass an empty list of assignments.")

        return self.late.loc[:, within].sum(axis=1)

    def forgive_lates(self, n, within=None):
        """Forgive the first n lates within a group of assignments.

        Parameters
        ----------
        n : int
            The number of lates to forgive.
        within : Sequence[str]
            A collection of assignment names that will be used to restrict the
            gradebook. If None, all assignments will be used. Default: None

        Notes
        -----
        By "first n", we mean in reference to the order specified by the `within`
        argument. As such, the `within` argument must be an ordered *sequence*.
        If not, a ValueError will be raised. For convenience, the result of
        Gradebook.assignments is an ordered sequence, and the order is guaranteed
        to be the same as the order of the underlying column names in the `points`
        table.

        If a late assignment is marked as dropped it will not be forgiven, as
        it is advantageous for the student to use the forgiveness elsewhere.

        Returns
        -------
        Gradebook
            The gradebook with the specified lates forgiven.

        Raises
        ------
        ValueError
            If `within` is empty, or if n is not a positive integer.
        TypeError
            If `within` is not an ordered sequence.

        """
        if n < 1:
            raise ValueError("Must forgive at least one late.")

        if within is None:
            within = self.assignments

        if not within:
            raise ValueError("Cannot pass an empty list of assignments.")

        new_late = self.late.copy()
        for pid in self.pids:
            forgiveness_remaining = n
            for assignment in within:
                is_late = self.late.loc[pid, assignment]
                is_dropped = self.dropped.loc[pid, assignment]
                if is_late and not is_dropped:
                    new_late.loc[pid, assignment] = False
                    forgiveness_remaining -= 1

                if forgiveness_remaining == 0:
                    break

        return self.replace(late=new_late)

    def _points_with_lates_replaced_by_zeros(self):
        replaced = self.points.copy()
        replaced[self.late.values] = 0
        return replaced

    def drop_lowest(self, n, within=None):
        """Drop the lowest n grades within a group of assignments.

        Parameters
        ----------
        n : int
            The number of grades to drop.
        within : Collection[str]
            A collection of assignment names that will be used to restrict the
            gradebook. If None, all assignments will be used. Default: None

        Notes
        -----
        Unless all assignments are worth the same number of points, dropping
        the lowest is non-trivial. Here, dropping assignments is performed via
        a brute-force algorithm: each possible combination of kept assignments
        is tested, and the one which yields the largest total_points /
        maximum_points_possible is used.  Therefore, this method is not
        recommended beyond small problem sizes.  For a better algorithm, see:
        http://cseweb.ucsd.edu/~dakane/droplowest.pdf

        If an assignment is marked as late, it will be considered a zero for
        the purposes of dropping. Therefore it is usually preferable to use
        .forgive_lates() before this method.

        If an assignment has already been marked as dropped, it won't be
        considered for dropping. This is useful, for instance, when a student's
        assignment is dropped due to an external circumstance.

        Returns
        -------
        Gradebook
            The gradebook with the specified assignments dropped.

        Raises
        ------
        ValueError
            If `within` is empty, or if n is not a positive integer.

        """
        # number of kept assignments
        if within is None:
            within = self.assignments

        if not within:
            raise ValueError("Cannot pass an empty list of assignments.")

        # convert to a list because Pandas likes lists, not Assignments objects
        within = list(within)

        # the combinations of assignments to drop
        combinations = list(itertools.combinations(within, n))

        # count lates as zeros
        points_with_lates_as_zeros = self._points_with_lates_replaced_by_zeros()[within]

        # a full table of maximum points available. this will allow us to have
        # different points available per person
        points_available = self.points.copy()[within]
        points_available.iloc[:, :] = self.maximums[within].values

        # we will try each combination and compute the resulting score for each student
        scores = []
        for possibly_dropped in combinations:
            possibly_dropped = list(possibly_dropped)
            possibly_dropped_mask = self.dropped.copy()
            possibly_dropped_mask[possibly_dropped] = True

            earned = points_with_lates_as_zeros.copy()
            earned[possibly_dropped_mask] = 0

            out_of = points_available.copy()
            out_of[possibly_dropped_mask] = 0

            score = earned.sum(axis=1) / out_of.sum(axis=1)
            scores.append(score)

        # now we put the scores into a table and find the index of the best
        # score for each student
        all_scores = pd.concat(scores, axis=1)
        index_of_best_score = all_scores.idxmax(axis=1)

        # loop through the students and mark the assignments which should be
        # dropped
        new_dropped = self.dropped.copy()
        for pid in self.pids:
            best_combo_ix = index_of_best_score.loc[pid]
            tossed = list(combinations[best_combo_ix])
            new_dropped.loc[pid, tossed] = True

        return self.replace(dropped=new_dropped)

    def replace(self, points=None, maximums=None, late=None, dropped=None):
        new_points = points if points is not None else self.points.copy()
        new_maximums = maximums if maximums is not None else self.maximums.copy()
        new_late = late if late is not None else self.late.copy()
        new_dropped = dropped if dropped is not None else self.dropped.copy()
        return Gradebook(new_points, new_maximums, new_late, new_dropped)

    def give_equal_weights(self, within):
        """Normalize maximum points so that all assignments are worth the same.

        Parameters
        ----------
        within : Collection[str]
            The assignments to reweight.

        Returns
        -------
        Gradebook

        """
        extra = set(within) - set(self.assignments)
        if extra:
            raise ValueError(f'These assignments are not in the gradebook: {extra}.')

        within = list(within)

        scores = self.points[within] / self.maximums[within]

        new_maximums = self.maximums.copy()
        new_maximums[within] = 1
        new_points = self.points.copy()
        new_points.loc[:, within] = scores

        return self.replace(points=new_points, maximums=new_maximums)

    def score(self, within):
        """Compute the score of the assignment group.

        Parameters
        ----------
        within : Collection[str]
            The assignments whose overall score should be computed.

        Returns
        -------
        float
            The score.

        """
        within = list(within)
        points_with_lates_as_zeros = self._points_with_lates_replaced_by_zeros()[within]

        # create a full array of points available
        points_available = self.points.copy()[within]
        points_available.iloc[:, :] = self.maximums[within].values

        effective_points = points_with_lates_as_zeros[~self.dropped].sum(axis=1)
        effective_possible = points_available[~self.dropped].sum(axis=1)

        return effective_points / effective_possible
