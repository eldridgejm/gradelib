"""Data structure for managing grades."""

import collections.abc
import itertools
import pathlib
import dataclasses
from typing import (
    Callable,
    Sequence,
    Mapping,
    Dict,
    List,
    Iterable,
    Union,
    Collection,
    Set,
    Tuple,
)

import pandas as pd

from . import io
from .types import Student


class Assignments(collections.abc.Sequence):
    """A sequence of assignments.

    Behaves essentially like a standard Python list, but has some additional
    methods which make it faster to create groups of assignments. In particular,
    :meth:`starting_with` and :meth:`containing`.
    """

    def __init__(self, names: Iterable[str]):
        self._names: List[str] = list(names)

    def __contains__(self, element):
        return element in self._names

    def __len__(self):
        return len(self._names)

    def __iter__(self):
        return iter(self._names)

    def starting_with(self, prefix: str) -> "Assignments":
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

    def containing(self, substring: str) -> "Assignments":
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

    def group_by(self, to_key: Callable[[str], str]) -> Dict[str, "Assignments"]:
        """Group the assignments according to a key function.

        Parameters
        ----------
        to_key : callable
            A function which accepts an assignment name and returns a string that will
            be used as the assignment's key in the resulting dictionary.

        Returns
        -------
        dict[str, Assignments]
            A dictionary mapping keys to collections of assignments.

        Example
        -------

        Suppose that the gradebook has assignments

            >>> assignments = gradelib.Assignments([
                "homework 01", "homework 01 - programming", "homework 02",
                "homework 03", "homework 03 - programming", "lab 01", "lab 02"
                ])
            >>> assignments.group_by(lambda s: s.split('-')[0].strip()
            {'homework 01': Assignments(names=['homework 01', 'homework 01 - programming']),
             'homework 02': Assignments(names=['homework 02']),
             'homework 03': Assignments(names=['homework 03', 'homework 03 - programming']),
             'lab 01': Assignments(names=['lab 01']),
             'lab 02': Assignments(names=['lab 02'])}

        See Also
        --------
        :meth:`Gradebook.unify_assignments`

        """
        dct: Dict[str, List[str]] = {}
        for assignment in self:
            key = to_key(assignment)
            if key not in dct:
                dct[key] = []
            dct[key].append(assignment)

        return {key: Assignments(value) for key, value in dct.items()}

    def __repr__(self):
        return f"Assignments(names={sorted(self._names)})"

    def __add__(self, other: "Assignments") -> "Assignments":
        return Assignments(set(self._names + other._names))

    def __getitem__(self, index):
        return self._names[index]


def _empty_mask_like(table: pd.DataFrame) -> pd.DataFrame:
    """Given a dataframe, create another just like it with every entry False."""
    empty = table.copy()
    empty.iloc[:, :] = False
    return empty.astype(bool)


def _lateness_in_seconds(lateness: pd.Series) -> pd.Series:
    """Converts a series of lateness strings in HH:MM:SS format to integer seconds"""
    hours = lateness.str.split(":").str[0].astype(int)
    minutes = lateness.str.split(":").str[1].astype(int)
    seconds = lateness.str.split(":").str[2].astype(int)
    return 3600 * hours + 60 * minutes + seconds


WithinSpecifier = Union[str, Sequence[str], Assignments]


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

    def __init__(
        self, points, maximums, late=None, dropped=None, groups=None
    ):
        self.points = points
        self.maximums = maximums
        self.late = late if late is not None else _empty_mask_like(points)
        self.dropped = dropped if dropped is not None else _empty_mask_like(points)
        self._groups = None

        if groups is None:
            self.groups = {}
            for assignment in self.points.columns:
                self.groups[assignment] = [assignment]
        else:
            self.groups = groups

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} object with "
            f"{len(self.assignments)} assignments "
            f"and {len(self.students)} students>"
        )

    @classmethod
    def from_gradescope(
        cls,
        path: Union[str, pathlib.Path],
        *,
        standardize_pids=True,
        standardize_assignments=True,
        lateness_fudge: int = 5 * 60,
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
        lateness_fudge : int
            An integer number of seconds. If the lateness of an assignment (in seconds)
            is less than or equal to this number, it will be counted as on-time. The
            default is 300 seconds (5 minutes). See note.

        Note
        ----
        The default `lateness_fudge` is 300 seconds. This default is
        recommended because Gradescope appears to exhibit some latency around
        deadlines. There have been cases where the CSV exported by gradescope
        will show a time of submission that is up to a minute later than what
        is displayed on the web interface. As a result, students see that their
        submission is on-time, but the exported CSV shows it as late. The fudge
        factor accounts for this.

        """
        points, maximums, lateness = io.read_gradescope(
            path,
            standardize_pids=standardize_pids,
            standardize_assignments=standardize_assignments,
        )
        # lates are given as strings expressing lateness... booleanize them
        late_seconds = lateness.apply(_lateness_in_seconds)
        late = late_seconds > lateness_fudge
        return cls(points, maximums, late)

    @classmethod
    def from_canvas(
        cls,
        path: Union[str, pathlib.Path],
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
    def combine(
        cls, gradebooks: Collection["Gradebook"], keep_pids=None
    ) -> "Gradebook":
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
        keep_pids : Collection[str] or None
            If provided, each input gradebook will be restricted to the PIDs
            given before attempting to combine them. This is a convenience
            option, and it simply calls :meth:`Gradebook.keep_pids` on
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

        if keep_pids is not None:
            gradebooks = [g.keep_pids(keep_pids) for g in gradebooks]

        # check that all gradebooks have the same PIDs
        reference_pids = gradebooks[0].pids
        for gradebook in gradebooks[1:]:
            if gradebook.pids != reference_pids:
                raise ValueError("Not all gradebooks have the same PIDs.")

        # check that all gradebooks have different assignment names
        number_of_assignments = sum(len(g.assignments) for g in gradebooks)
        unique_assignments: Set[str] = set()
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

    def merge_groups(
        self, group_names: Collection[str], name: str
    ) -> "Gradebook":
        """Merges the assignment groups to create a new assignment group."""
        if callable(group_names):
            group_names = list(filter(group_names, self.groups.keys()))

        if not set(group_names).issubset(self.groups.keys()):
            raise ValueError("Some group names are invalid.")

        assignments = []
        for group_name in group_names:
            assignments.extend(self.groups[group_name])

        new_group = assignments
        new_groups = self.groups.copy()

        # remove the old assignment groups that have been merged; do this
        # before adding new group in case the `name` is one of the old group
        # names, meaning that it is effectively replaced
        for group_name in group_names:
            del new_groups[group_name]

        new_groups[name] = new_group

        return self._replace(groups=new_groups)

    @property
    def assignments(self) -> Assignments:
        """All assignments in the gradebook.

        Returns
        -------
        Assignments

        """
        return Assignments(self.points.columns)

    @property
    def students(self) -> Set[Student]:
        """All student names and PIDs.

        Returns
        -------
        Set[Student]

        """
        return set(self.points.index)

    @property
    def pids(self) -> Set[str]:
        """All student PIDs.

        Returns
        -------
        set

        """
        return set(s.pid for s in self.students)

    @property
    def names(self) -> Set[str]:
        """All student names.

        Returns
        -------
        set

        """
        return set(s.names for s in self.students)

    def keep_pids(self, to: Collection[str]) -> "Gradebook":
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

        students = [s for s in self.students if s.pid in set(pids)]

        r_points = self.points.loc[students].copy()
        r_late = self.late.loc[students].copy()
        r_dropped = self.dropped.loc[students].copy()
        return self.__class__(r_points, self.maximums, r_late, r_dropped)

    def keep_assignments(self, assignments: Collection[str]) -> "Gradebook":
        """Restrict the gradebook to only the supplied assignments.

        Parameters
        ----------
        assignments : Collection[str]
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
        assignments = list(assignments)
        extras = set(assignments) - set(self.assignments)
        if extras:
            raise KeyError(f"These assignments were not in the gradebook: {extras}.")

        r_points = self.points.loc[:, assignments].copy()
        r_maximums = self.maximums[assignments].copy()
        r_late = self.late.loc[:, assignments].copy()
        r_dropped = self.dropped.loc[:, assignments].copy()
        return self.__class__(r_points, r_maximums, r_late, r_dropped)

    def remove_assignments(self, assignments: Collection[str]) -> "Gradebook":
        """Remove the assignments from the gradebook.

        Parameters
        ----------
        assignments : Collection[str]
            A collection of assignment names.

        Returns
        -------
        Gradebook
            A Gradebook without these assignments.

        Raises
        ------
        KeyError
            If an assignment was specified that was not in the gradebook.

        """
        assignments = list(assignments)
        extras = set(assignments) - set(self.assignments)
        if extras:
            raise KeyError(f"These assignments were not in the gradebook: {extras}.")

        return self.keep_assignments(set(self.assignments) - set(assignments))

    def _get_assignments(self, within_spec: WithinSpecifier):
        if isinstance(within_spec, str):
            return self.groups[within_spec]
        elif isinstance(within_spec, Assignments):
            return list(within_spec)
        else:
            # it must be a list of group names
            assignments = []
            for group in self.groups.values():
                assignments.extend(group)
            return assignments

    def number_of_lates(self, within: WithinSpecifier) -> pd.Series:
        """Return the number of late assignments for each student as a Series.

        Parameters
        ----------
        within : WithinSpecifier
            The assignments to count lates within.

        Returns
        -------
        pd.Series
            A series mapping PID to number of late assignments.

        Raises
        ------
        ValueError
            If `within` is empty.

        """
        assignments = self._get_assignments(within)
        return self.late.loc[:, assignments].sum(axis=1)

    def forgive_lates(self, n: int, within: WithinSpecifier) -> "Gradebook":
        """Forgive the first n lates within a group of assignments.

        Parameters
        ----------
        n : int
            The number of lates to forgive.
        within : WithinSpecifier
            Assignments within which to forgive lates. Assignments are forgiven in the
            order that they appear.

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

        assignments = self._get_assignments(within)

        new_late = self.late.copy()
        for student in self.students:
            forgiveness_remaining = n
            for assignment in assignments:
                is_late = self.late.loc[student, assignment]
                is_dropped = self.dropped.loc[student, assignment]
                if is_late and not is_dropped:
                    new_late.loc[student, assignment] = False
                    forgiveness_remaining -= 1

                if forgiveness_remaining == 0:
                    break

        return self._replace(late=new_late)

    def _points_with_lates_replaced_by_zeros(self) -> pd.DataFrame:
        replaced = self.points.copy()
        replaced[self.late.values] = 0
        return replaced

    def drop_lowest(self, n: int, within: WithinSpecifier) -> "Gradebook":
        """Drop the lowest n grades within a group of assignments.

        Parameters
        ----------
        n : int
            The number of grades to drop.
        within : WithinSpecifier
            The assignments to drop within.

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
            If `n` is not a positive integer.

        """
        assignments = self._get_assignments(within)

        # the combinations of assignments to drop
        combinations = list(itertools.combinations(assignments, n))

        # count lates as zeros
        points_with_lates_as_zeros = self._points_with_lates_replaced_by_zeros()[assignments]

        # a full table of maximum points available. this will allow us to have
        # different points available per person
        points_available = self.points.copy()[assignments]
        points_available.iloc[:, :] = self.maximums[assignments].values

        # we will try each combination and compute the resulting score for each student
        scores = []
        for possibly_dropped in combinations:
            possibly_dropped_mask = self.dropped.copy()
            possibly_dropped_mask[list(possibly_dropped)] = True

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
        for student in self.students:
            best_combo_ix = index_of_best_score.loc[student]
            tossed = list(combinations[best_combo_ix])
            new_dropped.loc[student, tossed] = True

        return self._replace(dropped=new_dropped)

    def _replace(
        self,
        points=None,
        maximums=None,
        late=None,
        dropped=None,
        groups=None,
    ) -> "Gradebook":

        new_points = points if points is not None else self.points.copy()
        new_maximums = maximums if maximums is not None else self.maximums.copy()
        new_late = late if late is not None else self.late.copy()
        new_dropped = dropped if dropped is not None else self.dropped.copy()
        new_groups = (
            groups
            if groups is not None
            else self.groups.copy()
        )

        return Gradebook(
            new_points, new_maximums, new_late, new_dropped, new_groups
        )

    def copy(self):
        return self._replace()

    def give_equal_weights(self, within: WithinSpecifier) -> "Gradebook":
        """Normalize maximum points so that all assignments are worth the same.

        Parameters
        ----------
        within : WithinSpecifier
            The assignments to reweight.

        Returns
        -------
        Gradebook

        """
        within = self._get_assignments(within)

        extra = set(within) - set(self.assignments)
        if extra:
            raise ValueError(f"These assignments are not in the gradebook: {extra}.")

        within = list(within)

        scores = self.points[within] / self.maximums[within]

        new_maximums = self.maximums.copy()
        new_maximums[within] = 1
        new_points = self.points.copy()
        new_points.loc[:, within] = scores

        return self._replace(points=new_points, maximums=new_maximums)

    def total(self, within: WithinSpecifier) -> Tuple[pd.Series, pd.Series]:
        """Computes the total points earned and available within one or more assignments.

        Takes into account late assignments (treats them as zeros) and dropped
        assignments (acts as if they were never assigned).

        Parameters
        ----------
        within : WithinSpecifier
            The assignments whose total points will be calculated

        Returns
        -------
        pd.Series
            The total points earned by each student.
        pd.Series
            The total points available for each student.

        """
        within = self._get_assignments(within)

        points_with_lates_as_zeros = self._points_with_lates_replaced_by_zeros()[within]

        # create a full array of points available
        points_available = self.points.copy()[within]
        points_available.iloc[:, :] = self.maximums[within].values

        effective_points = points_with_lates_as_zeros[~self.dropped].sum(axis=1)
        effective_possible = points_available[~self.dropped].sum(axis=1)

        return effective_points, effective_possible

    def score(self, within: Collection[str]) -> pd.Series:
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

    def _unify_assignment(self, new_name: str, parts: Collection[str]) -> "Gradebook":
        """A helper function to unify assignments under the new name."""
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

    def unify_assignments(
        self,
        dct_or_callable: Union[Mapping[str, Collection[str]], Callable[[str], str]],
    ) -> "Gradebook":
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
        dct : Mapping[str, Collection[str]]
            Either: 1) a mapping whose keys are new assignment names, and whose
            values are collections of assignments that should be unified under
            their common key; or 2) a callable which maps assignment names to
            new assignment by which they should be grouped.

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

        Example
        -------

        Assuming the gradebook has assignments named `homework 01`, `homework 01 - programming`,
        `homework 02`, `homework 02 - programming`, etc., the following will "unify" the
        assignments into `homework 01`, `homework 02`, etc:

            >>> gradebook.unify_assignments(lambda s: s.split('-')[0].strip())

        Alternatively, you could write:

            >>> gradebook.unify_assignments({
                'homework 01': {'homework 01', 'homework 01 - programming'},
                'homework 02': {'homework 02', 'homework 02 - programming'}
                })

        """
        dct: Dict[str, List[str]] = {}
        if not callable(dct_or_callable):
            dct = {k: list(v) for (k, v) in dct_or_callable.items()}
        else:
            to_key = dct_or_callable
            dct = {}
            for assignment in self.assignments:
                key = to_key(assignment)
                if key not in dct:
                    dct[key] = []
                dct[key].append(assignment)

        result = self
        for key, value in dct.items():
            result = result._unify_assignment(key, value)
        return result

    def add_assignment(
        self,
        name: str,
        points: pd.Series,
        maximums: pd.Series,
        late: pd.Series = None,
        dropped=None,
    ):
        """Adds a single assignment to the gradebook.

        The assignment will be placed in its own group.

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
            late = pd.Series(False, index=self.students)

        if dropped is None:
            dropped = pd.Series(False, index=self.students)

        result = self.copy()

        def _match_students(students, where):
            theirs = set(students)
            ours = set(self.students)
            if theirs - ours:
                raise ValueError(
                    f'Unknown students {theirs - ours} provided in "{where}".'
                )
            if ours - theirs:
                raise ValueError(f'"{where}" is missing students: {ours - theirs}')

        _match_students(points.index, "points")
        _match_students(late.index, "late")
        _match_students(dropped.index, "dropped")

        result.points[name] = points
        result.maximums[name] = maximums
        result.late[name] = late
        result.dropped[name] = dropped

        result.groups[name] = [name]

        return result
