"""Data structure for managing grades."""

import collections.abc
import itertools

import pandas as pd

from . import io


class Assignments(collections.abc.Sequence):
    """A sequence of assignments.

    Behaves essentially like a standard Python list, but has some additional
    methods which make it faster to create groups of assignments. In particular,
    :meth:`starting_with` and :meth:`containing`.
    """

    def __init__(self, names):
        self._names = list(names)

    def __contains__(self, element):
        return element in self._names

    def __len__(self):
        return len(self._names)

    def __iter__(self):
        return iter(self._names)

    def starting_with(self, prefix):
        """Return only assignments starting with the prefix.

        Parameters
        ----------
        prefix : str
            The prefix to search for.

        Returns
        -------
        Assignments
            Only those assignments starting with the prefix.

        """
        return self.__class__(x for x in self._names if x.startswith(prefix))

    def containing(self, substring):
        """Return only assignments containing the substring.

        Parameters
        ----------
        substring : str
            The substring to search for.

        Returns
        -------
        Assignments
            Only those assignments containing the substring.

        """
        return self.__class__(x for x in self._names if substring in x)

    def __repr__(self):
        return f"Assignments(names={self._names})"

    def __add__(self, other):
        return Assignments(set(self._names + other._names))

    def __getitem__(self, index):
        return self._names[index]


def _empty_mask_like(table):
    """Given a dataframe, create another just like it with every entry False."""
    empty = table.copy()
    empty.iloc[:, :] = False
    return empty.astype(bool)


class Gradebook:
    """Data structure which facilitates common grading policies.

    Parameters
    ----------
    points : pandas.DataFrame
        A dataframe with one row per student, and one column for each assignment.
        Each entry should be the number of points earned by the student on the
        given assignment. The index of the dataframe should consist of student
        PIDs.
    maximums : pandas.Series
        A series containing the maximum number of points possible for each
        assignment. The index of the series should match the columns of the
        `points` dataframe.
    late : pandas.DataFrame
        A Boolean dataframe with the same columns/index as `points`. An entry
        that is `True` indicates that the assignment was late. If `None` is 
        passed, a dataframe of all `False`s is used by default.
    dropped : pandas.DataFrame
        A Boolean dataframe with the same columns/index as `points`. An entry
        that is `True` indicates that the assignment should be dropped. If
        `None` is passed, a dataframe of all `False`s is used by default.

    Notes
    -----
    Typically a Gradebook is not created manually, but is instead produced
    by reading grades exported from Gradescope or Canvas, using
    :func:`read_gradescope_gradebook` or :func:`read_canvas_gradebook`.

    """

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
    def from_gradescope(
        cls, path, *, standardize_pids=True, standardize_assignments=True
    ):
        """Read a gradescope CSV into a gradebook.

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
        points, maximums, late = io.read_gradescope(
            path,
            standardize_pids=standardize_pids,
            standardize_assignments=standardize_assignments,
        )
        # lates are given as strings expressing lateness... booleanize them
        late = (late != "00:00:00").astype(bool)
        return cls(points, maximums, late)

    @classmethod
    def from_canvas(
        cls,
        path,
        *,
        standardize_pids=True,
        standardize_assignments=True,
        remove_assignment_ids=True,
    ):
        """Read a CSV exported from Canvas.

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

        """
        points, maximums = io.read_canvas(
            path,
            standardize_pids=standardize_pids,
            standardize_assignments=standardize_assignments,
            remove_assignment_ids=remove_assignment_ids,
        )
        return cls(points, maximums)

    @classmethod
    def combine(cls, gradebooks, restrict_pids=None):
        """Create a gradebook by safely combining several existing gradebooks.

        It is crucial that the combined gradebooks have exactly the same
        students -- we don't want students to have missing grades. This
        function checks to make sure that the gradebooks have the same students
        before combining them. Similarly, it verifies that each gradebook has
        unique assignments, so that no conflicts occur when combining them.

        Parameters
        ----------
        gradebooks : Collection[Gradebook]
            The gradebooks to combine. Must have matching indices and unique
            column names.
        restrict_pids : Collection[str] or None
            If provided, each input gradebook will be restricted to the PIDs
            given before attempting to combine them. This is a convenience
            option, and it simply calls :meth:`Gradebook.restrict_pids` on
            each of the inputs.  Default: None

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
        def concat_attr(a, axis=1):
            """Create a DF/Series by combining the same attribute across gradebooks."""
            all_tables = [getattr(g, a) for g in gradebooks]
            return pd.concat(all_tables, axis=axis)

        points = concat_attr("points")
        maximums = concat_attr("maximums", axis=0)
        late = concat_attr("late")
        dropped = concat_attr("dropped")

        return cls(points, maximums, late, dropped)

    @property
    def assignments(self):
        """All assignments in the gradebook.

        Returns
        -------
        Assignments

        """
        return Assignments(self.points.columns)

    @property
    def pids(self):
        """All student PIDs.

        Returns
        -------
        set

        """
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
            A collection of assignments within which lates will be forgiven.
            If None, all assignments will be used. Default: None

        Notes
        -----
        By "first n", we mean with respect to the order specified by the `within`
        argument. As such, the `within` argument must be an ordered *sequence*.
        If not, a ValueError will be raised. For convenience, the result of
        :attr:`Gradebook.assignments` is an ordered sequence, and the order is guaranteed
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
            A collection of assignments; the lowest among them will be dropped.
            If None, all assignments will be used. Default: None

        Notes
        -----
        If all assignments are worth the same number of points, dropping the
        assignment with the lowest score is most advantageous to the student.
        However, if the assignments are not worth the same number of points,
        the best strategy for the student is not necessarily to drop to
        assignment with the smallest score. In this case, the problem of
        determining the optimal set of assignments to drop in order to maximize
        the overall score is non-trivial.

        In this implementation, dropping assignments is performed via a
        brute-force algorithm: each possible combination of kept assignments is
        tested, and the one which yields the largest total_points /
        maximum_points_possible is used. The time complexity of this approach
        is combinatorial, and therefore it is not recommended beyond small
        problem sizes. For a better algorithm, see:
        http://cseweb.ucsd.edu/~dakane/droplowest.pdf

        If an assignment is marked as late, it will be considered a zero for
        the purposes of dropping. Therefore it is usually preferable to use
        :meth:`Gradebook.forgive_lates` before this method.

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

    def copy(self):
        return self.replace()

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
            raise ValueError(f"These assignments are not in the gradebook: {extra}.")

        within = list(within)

        scores = self.points[within] / self.maximums[within]

        new_maximums = self.maximums.copy()
        new_maximums[within] = 1
        new_points = self.points.copy()
        new_points.loc[:, within] = scores

        return self.replace(points=new_points, maximums=new_maximums)

    def total(self, within):
        """Computes the total points earned and available within one or more assignments.

        Takes into account late assignments (treats them as zeros) and dropped
        assignments (acts as if they were never assigned).

        Parameters
        ----------
        within : Collection[str]
            The assignments whose total points will be calculated

        Returns
        -------
        pd.Series
            The total points earned by each student.
        pd.Series
            The total points available for each student.

        """
        if isinstance(within, str):
            within = [within]
        else:
            within = list(within)

        points_with_lates_as_zeros = self._points_with_lates_replaced_by_zeros()[within]

        # create a full array of points available
        points_available = self.points.copy()[within]
        points_available.iloc[:, :] = self.maximums[within].values

        effective_points = points_with_lates_as_zeros[~self.dropped].sum(axis=1)
        effective_possible = points_available[~self.dropped].sum(axis=1)

        return effective_points, effective_possible

    def score(self, within):
        """Computes the fraction of possible points earned across one or more assignments.

        Takes into account late assignments (treats them as zeros) and dropped
        assignments (acts as if they were never assigned).

        Parameters
        ----------
        within : Collection[str]
            The assignments whose overall score should be computed.

        Returns
        -------
        pd.Series
            The score for each student as a number between 0 and 1.

        """
        earned, available = self.total(within)
        return earned / available

    def unify(self, parts, new_name):
        """Unifies the assignment parts into one single assignment with the new name.

        Sometimes assignments may have several parts which are recorded separately
        in the grading software. For instance, a homework might
        have a written part and a programming part. This method makes it easy
        to unify these parts into a single assignment.

        The new point total and maximum possible points are calculated by
        addition. The new assignment is considered late if either of the parts
        are marked as late.

        It is unclear what the result should be if any of the assignments to be
        unified has been dropped, but other parts have not. For this reason,
        this method will raise a `ValueError` if *any* of the parts have been
        dropped.

        Parameters
        ----------
        parts : Collection[str]
            The assignments that should be unified into one assignment.
        new_name : str
            The name that should be given to the new assignment.

        Returns
        -------
        Gradebook
            The gradebook with the assignments unified to one assignment. Other 
            assignments are left untouched.

        Raises
        ------
        ValueError
            If any of the assignments to be unified is marked as dropped. See above for
            rationale.

        """
        parts = list(parts)
        if self.dropped[parts].any(axis=None):
            raise ValueError("Cannot unify assignments with drops.")

        assignment_points = self.points[parts].sum(axis=1)
        assignment_max = self.maximums[parts].sum()
        assignment_late = self.late[parts].any(axis=1)

        new_points = self.points.copy().drop(columns=parts)
        new_max = self.maximums.copy().drop(parts)
        new_late = self.late.copy().drop(columns=parts)

        new_points[new_name] = assignment_points
        new_max[new_name] = assignment_max
        new_late[new_name] = assignment_late

        return Gradebook(new_points, new_max, late=new_late)

    def add_assignment(self, name, points, maximums, late=None, dropped=None):
        """Adds a single assignment to the gradebook.

        Usually Gradebook do not need to have individual assignments added to them.
        Instead, Gradebooks are read from Canvas, Gradescope, etc. In some instances,
        though, it can be useful to manually add an assignment to a Gradebook -- this
        method makes it easy to do so.

        Parameters
        ----------
        name : str
            The name of the new assignment. Must be unique.
        points : Series[float]
            A Series of points earned by each student.
        maximums : float
            The maximum number of points possible on the assignment.
        late : Series[bool]
            Whether each student turned in the assignment late. Default: all False.
        dropped : Series[bool]
            Whether the assignment should be dropped for any given student. Default:
            all False.

        Returns
        -------
        Gradebook
            A new Gradebook object with the new assignment in place.

        Raises
        ------
        ValueError
            If an assignment with the given name already exists, or if grades for a student
            are missing / grades for an unknown student are provided.

        """
        if name in self.assignments:
            raise ValueError(f'An assignment with the name "{name}" already exists.')

        if late is None:
            late = pd.Series(False, index=self.pids)

        if dropped is None:
            dropped = pd.Series(False, index=self.pids)

        result = self.copy()

        def _match_pids(pids, where):
            theirs = set(pids)
            ours = set(self.pids)
            if theirs - ours:
                raise ValueError(f'Unknown pids {theirs - ours} provided in "{where}".')
            if ours - theirs:
                raise ValueError(f'"{where}" is missing PIDs: {ours - theirs}')

        _match_pids(points.index, "points")
        _match_pids(late.index, "late")
        _match_pids(dropped.index, "dropped")

        result.points[name] = points
        result.maximums[name] = maximums
        result.late[name] = late
        result.dropped[name] = dropped

        return result
