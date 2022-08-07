"""Data structure for managing grades."""

import collections.abc
import itertools
import copy

import pandas as pd


class Student:
    def __init__(self, pid, name=None):
        self.pid = pid
        self.name = name

    def __repr__(self):
        if self.name is not None:
            s = self.name
        else:
            s = self.pid

        return f"<{s}>"

    def __hash__(self):
        return hash(self.pid)

    def __eq__(self, other):
        if isinstance(other, Student):
            return other.pid == self.pid
        else:
            return self.pid == other


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

    def group_by(self, to_key: callable):
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
        dct = {}
        for assignment in self:
            key = to_key(assignment)
            if key not in dct:
                dct[key] = []
            dct[key].append(assignment)

        return {key: Assignments(value) for key, value in dct.items()}

    def __repr__(self):
        return f"Assignments(names={sorted(self._names)})"

    def __add__(self, other):
        return Assignments(set(self._names + other._names))

    def __getitem__(self, index):
        return self._names[index]


class PointsDeduction:
    def __init__(self, points, note):
        self.points = points
        self.note = note


class PercentageDeduction:
    def __init__(self, percentage, note):
        self.percentage = percentage
        self.note = note


def _empty_mask_like(table):
    """Given a dataframe, create another just like it with every entry False."""
    empty = table.copy()
    empty.iloc[:, :] = False
    return empty.astype(bool)


def _empty_lateness_like(table):
    """Given a dataframe, create another just like it with every entry a timedelta of 0."""
    empty = table.copy()
    empty.iloc[:, :] = 0
    for column in empty.columns:
        empty[column] = pd.to_timedelta(empty[column], unit="s")
    return empty


DEFAULT_OPTS = {"lateness_fudge": 5 * 60}


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
        self,
        points_marked,
        points_available,
        lateness=None,
        dropped=None,
        deductions=None,
        opts=None,
    ):
        self.points_marked = points_marked
        self.points_available = points_available
        self.lateness = (
            lateness if lateness is not None else _empty_lateness_like(points_marked)
        )
        self.dropped = (
            dropped if dropped is not None else _empty_mask_like(points_marked)
        )
        self.opts = opts if opts is not None else DEFAULT_OPTS
        self.deductions = {} if deductions is None else deductions

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} object with "
            f"{len(self.assignments)} assignments "
            f"and {len(self.pids)} students>"
        )

    @property
    def late(self):
        fudge = self.opts["lateness_fudge"]
        return self.lateness > pd.Timedelta(fudge, unit="s")

    @classmethod
    def combine(cls, gradebooks, keep_pids=None):
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

        points = concat_attr("points_marked")
        maximums = concat_attr("points_available", axis=0)
        lateness = concat_attr("lateness")
        dropped = concat_attr("dropped")

        return cls(points, maximums, lateness, dropped)

    @property
    def assignments(self):
        """All assignments in the gradebook.

        Returns
        -------
        Assignments

        """
        return Assignments(self.points_marked.columns)

    @property
    def pids(self):
        """All student PIDs.

        Returns
        -------
        set

        """
        return set(self.points_marked.index)

    @property
    def points_after_deductions(self):
        points = self.points_marked.copy()

        def _apply_deduction(pid, assignment, deduction):
            p = points.loc[pid, assignment]

            if isinstance(deduction, PointsDeduction):
                d = deduction.points
            else:
                d = deduction.percentage * p

            points.loc[pid, assignment] = max(p - d, 0)

        for pid, assignments_dct in self.deductions.items():
            for assignment, deductions in assignments_dct.items():
                for deduction in deductions:
                    _apply_deduction(pid, assignment, deduction)

        return points

    def keep_pids(self, to):
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

        r_points = self.points_marked.loc[pids].copy()
        r_lateness = self.lateness.loc[pids].copy()
        r_dropped = self.dropped.loc[pids].copy()
        return self.__class__(r_points, self.points_available, r_lateness, r_dropped)

    def keep_assignments(self, assignments):
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

        r_points = self.points_marked.loc[:, assignments].copy()
        r_maximums = self.points_available[assignments].copy()
        r_lateness = self.lateness.loc[:, assignments].copy()
        r_dropped = self.dropped.loc[:, assignments].copy()
        return self.__class__(r_points, r_maximums, r_lateness, r_dropped)

    def remove_assignments(self, assignments):
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

    def _replace(self, **kwargs):
        kwarg_names = [
            "points_marked",
            "points_available",
            "lateness",
            "dropped",
            "deductions",
            "opts",
        ]

        extra = set(kwargs.keys()) - set(kwarg_names)
        assert not extra, f"Invalid kwargs provided: {extra}"

        def _copy(obj):
            if hasattr(obj, "copy"):
                return obj.copy()
            else:
                return copy.deepcopy(obj)

        new_kwargs = {}
        for kwarg_name in kwarg_names:
            if kwarg_name in kwargs:
                new_kwargs[kwarg_name] = kwargs[kwarg_name]
            else:
                new_kwargs[kwarg_name] = _copy(getattr(self, kwarg_name))

        return Gradebook(**new_kwargs)

    def copy(self):
        return self._replace()

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

        scores = self.points_marked[within] / self.points_available[within]

        new_points_available = self.points_available.copy()
        new_points_available[within] = 1
        new_points_marked = self.points_marked.copy()
        new_points_marked.loc[:, within] = scores

        return self._replace(
            points_marked=new_points_marked, points_available=new_points_available
        )

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

        points_with_lates_as_zeros = self.points_marked.copy()
        points_with_lates_as_zeros[self.late.values] = 0

        # create a full array of points available
        points_available = self.points_marked.copy()[within]
        points_available.iloc[:, :] = self.points_available[within].values

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

    def _unify_assignment(self, new_name, parts):
        """A helper function to unify assignments under the new name."""
        parts = list(parts)
        if self.dropped[parts].any(axis=None):
            raise ValueError("Cannot unify assignments with drops.")

        assignment_points = self.points_marked[parts].sum(axis=1)
        assignment_max = self.points_available[parts].sum()
        assignment_lateness = self.lateness[parts].max(axis=1)

        new_points = self.points_marked.copy().drop(columns=parts)
        new_max = self.points_available.copy().drop(parts)
        new_lateness = self.lateness.copy().drop(columns=parts)

        new_points[new_name] = assignment_points
        new_max[new_name] = assignment_max
        new_lateness[new_name] = assignment_lateness

        return Gradebook(new_points, new_max, lateness=new_lateness)

    def unify_assignments(self, dct_or_callable):
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
        if self.deductions:
            raise NotImplementedError("Cannot unify if deductions have been defined.")

        if not callable(dct_or_callable):
            dct = dct_or_callable
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

    def add_assignment(self, name, points, maximums, lateness=None, dropped=None):
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

        if lateness is None:
            lateness = pd.to_timedelta(pd.Series(0, index=self.pids), unit="s")

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
        _match_pids(lateness.index, "late")
        _match_pids(dropped.index, "dropped")

        result.points_marked[name] = points
        result.points_available[name] = maximums
        result.lateness[name] = lateness
        result.dropped[name] = dropped

        return result
