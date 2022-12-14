"""Core type for managing a collection of grades."""

from __future__ import annotations

import copy
import dataclasses
import typing
import math
import collections.abc

from ..scales import DEFAULT_SCALE, map_scores_to_letter_grades
from .student import Student, Students
from .assignments import Assignments, AssignmentSelector, normalize

import numpy as np
import pandas as pd


# private helper functions ---------------------------------------------------------------------


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


def _cast_index(df):
    """Ensure that the dataframe index contains Student objects."""

    def _cast(x):
        if isinstance(x, Student):
            return x
        else:
            return Student(x)

    df.index = [_cast(x) for x in df.index]
    return df


def _concatenate_notes(gradebooks):
    """Concatenates the notes from a sequence of gradebooks."""
    notes = {}
    for gradebook in gradebooks:
        for pid, channels_dct in gradebook.notes.items():
            if pid not in notes:
                notes[pid] = {}

            for channel, messages in channels_dct.items():
                if channel not in notes[pid]:
                    notes[pid][channel] = []

                notes[pid][channel].extend(messages)

    return notes


def _concatenate_groups(gradebooks):
    """Concatenates the groups from a sequence of gradebooks."""
    new_groups = {}
    for gradebook in gradebooks:
        for group_name, group in gradebook.grading_groups.items():
            if group_name in new_groups:
                raise ValueError(f"Duplicate group names seen: {group_name}.")
            new_groups[group_name] = group
    return new_groups


def _combine_if_equal(gradebooks: typing.Collection["Gradebook"], attr: str):
    """Checks that the attribute is the same in all gradebooks.

    If it is, the common attribute is returned. Otherwise, a `ValueError` is raised.

    """
    obj = None
    for gradebook in gradebooks:
        if obj is None:
            obj = getattr(gradebook, attr)
        else:
            if getattr(gradebook, attr) != obj:
                raise ValueError("Objects do not match in all gradebooks.")

    return obj


# public functions ---------------------------------------------------------------------


def combine_gradebooks(
    gradebooks: typing.Collection["Gradebook"], restrict_to_students=None
):
    """Create a gradebook by safely combining several existing gradebooks.

    It is crucial that the combined gradebooks have exactly the same students
    -- we don't want students to have missing grades. This function checks to
    make sure that the gradebooks have the same students before combining them.
    Similarly, it verifies that each gradebook has unique assignments and group
    names, so that no conflicts occur when combining them.

    The new gradebook's assignments groups are reset; there are no groups.

    If the scales are the same, the new scale is set to be the same as the old.
    If they are different, a `ValueError` is raised.

    If the options are the same, the new options are set to be the same as the
    old. If they are different, a `ValueError` is raised.

    Parameters
    ----------
    gradebooks : Collection[Gradebook]
        The gradebooks to combine. Must have matching indices and unique
        column names.
    restrict_to_students : Optional[Collection[str]]
        If provided, each input gradebook will be restrict to the PIDs
        given before attempting to combine them. This is a convenience
        option, and it simply calls :meth:`Gradebook.restrict_to_students` on
        each of the inputs.  Default: None

    Returns
    -------
    Gradebook
        A gradebook combining all of the input gradebooks.

    Raises
    ------
    ValueError
        If the PID indices of gradebooks do not match; if there is a duplicate
        assignment name; a duplicate group name; the options do not match; the
        scales do not match.

    """
    gradebooks = [g.copy() for g in gradebooks]

    if restrict_to_students is not None:
        for gradebook in gradebooks:
            gradebook.restrict_to_students(restrict_to_students)

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

    return Gradebook(
        points_earned=concat_attr("points_earned"),
        points_possible=concat_attr("points_possible", axis=0),
        lateness=concat_attr("lateness"),
        dropped=concat_attr("dropped"),
        notes=_concatenate_notes(gradebooks),
        grading_groups={},
        opts=_combine_if_equal(gradebooks, "opts"),
        scale=_combine_if_equal(gradebooks, "scale"),
    )


# GradebookOptions ---------------------------------------------------------------------


@dataclasses.dataclass
class GradebookOptions:
    """Configures the behavior of a :class:`Gradebook`.

    Attributes
    ----------
    lateness_fudge: int
        Number of seconds within which a late assignment is not considered late
        by :meth:`Gradebook.late`. This can be useful to work around grade
        sources where the lateness may not be reliable, such as Gradescope.
        Default: 300.

    allow_extra_credit: bool
        If `True`, grading group weights are allowed to sum to beyond one,
        effectively allowing extra credit. Default: `False`.

    """

    lateness_fudge: int = 5 * 60
    allow_extra_credit: bool = False


# GradingGroup --------------------------------------------------------------------------------


class GradingGroup:
    """Represents a logical group of assignments and their weights.

    Attributes
    ----------
    assignment_weights: dict[str, float]
        A dictionary mapping assignment names (strings) to their weight within
        the group (as a float between 0 and 1). Their weights should add to
        one.
    group_weight: float
        The overall weight of the group.

    Raises
    ------
    ValueError
        If the assignment weights are not between 0 and 1, they do not add to
        one, or if the group weight is not between 0 and 1.
    TypeError
        If the assignment weights are not in the form of a dictionary.
    """

    _attrs = [
        "assignment_weights",
        "group_weight",
    ]

    def __init__(
        self,
        assignment_weights,
        group_weight,
    ):

        if not isinstance(assignment_weights, dict):
            raise TypeError("Must be a dictionary.")

        if not assignment_weights:
            raise ValueError("Assignment weights cannot be empty.")

        if not math.isclose(sum(assignment_weights.values()), 1):
            raise ValueError("Assignment weights must sum to one.")

        if not all(0 <= w <= 1 for w in assignment_weights.values()):
            raise ValueError("Assignment weights must be between 0 and 1.")

        if not 0 <= group_weight <= 1:
            raise ValueError("Group weight must be between 0 and 1.")

        self.assignment_weights = assignment_weights
        self.group_weight = group_weight

    def __repr__(self):
        return (
            f"GradingGroup(assignment_weights={self.assignment_weights!r}, "
            f"group_weight={self.group_weight!r})"
        )

    @property
    def assignments(self) -> Assignments:
        """The assignments in the group."""
        return Assignments(self.assignment_weights)

    def __eq__(self, other):
        return all(getattr(self, attr) == getattr(other, attr) for attr in self._attrs)


# Gradebook ============================================================================


class Gradebook:
    """Data structure which facilitates common grading operations.

    Typically a Gradebook is not created manually, but is instead produced by
    reading grades exported from Gradescope or Canvas, using
    :func:`gradelib.io.gradescope.read` or :func:`gradelib.io.canvas.read`.


    Parameters
    ----------
    points_earned : pandas.DataFrame
        A dataframe with one row per student, and one column for each
        assignment. Each entry should be the raw number of points earned by the
        student on the given assignment. The index of the dataframe should
        consist of :class:`Student` objects.
    points_possible : pandas.Series
        A series containing the maximum number of points possible for each
        assignment. The index of the series should match the columns of the
        `points_earned` dataframe.
    lateness : Optional[pandas.DataFrame]
        A dataframe of `pd.Timedelta` objects with the same columns/index as
        `points_earned`. An entry in the dataframe records how late a student
        turned in the assignment. If `None` is passed, a dataframe of zero
        second timedeltas is used by default.
    dropped : Optional[pandas.DataFrame]
        A Boolean dataframe with the same columns/index as `points_earned`. An
        entry that is `True` indicates that the assignment should be dropped.
        If `None` is passed, a dataframe of all `False` is used by default.
    notes : Optional[dict]
        A nested dictionary of notes, possibly used by report generating code.
        The keys of the outer dictionary should be student PIDs, and the values
        should be dictionaries. The keys of the inner dictionary should specify
        a note "channel", and can be either "late", "drop", or "misc"; these
        are signals to reporting code that help determine where to display
        notes. The values of the inner dictionary should be iterables of
        strings, each one a message.
    opts : Optional[GradebookOptions]
        An optional collection of options configuring the behavior of the
        Gradebook.

    Attributes
    ----------
    points_earned : pandas.DataFrame
        A dataframe with one row per student, and one column for each
        assignment. Each entry is the raw number of points earned by the
        student on the given assignment. The index of the dataframe should
        consist of :class:`Student` objects. This dataframe can be modified.
    points_possible : pandas.Series
        A series containing the maximum number of points possible for each
        assignment. The index of the series should match the columns of the
        `points_earned` dataframe. This Series can be modified.
    lateness : Optional[pandas.DataFrame]
        A dataframe of `pd.Timedelta` objects with the same columns/index as
        `points_earned`. An entry in the dataframe records how late a student
        turned in the assignment. If `None` is passed, a dataframe of zero
        second timedeltas is used by default. See :attr:`late` for a Boolean
        version of the lateness. This dataframe can be modified.
    dropped : Optional[pandas.DataFrame]
        A Boolean dataframe with the same columns/index as `points_earned`. An
        entry that is `True` indicates that the assignment should be dropped.
        If `None` is passed, a dataframe of all `False` is used by default.
        This dataframe can be modified.
    notes : Optional[dict]
        A nested dictionary of notes, possibly used by report generating code.
        The keys of the outer dictionary should be student PIDs, and the values
        should be dictionaries. The keys of the inner dictionary should specify
        a note "channel", and can be either "late", "drop", or "misc"; these
        are signals to reporting code that help determine where to display
        notes. The values of the inner dictionary should be iterables of
        strings, each one a message. Can be modified.
    opts : Optional[GradebookOptions]
        An optional collection of options configuring the behavior of the
        Gradebook.
    grading_groups : dict[str, GradingGroup]
        A mapping from assignment group names (strings) to :class:`GradingGroup`
        objects representing a group of assignments. The default is simply ``{}``.

        To prevent unintentional errors, the grading groups must be set before
        accessive summative attributes, such as :attr:`overall_score`.

        While the dictionary returned by this attribute has
        :class:`GradingGroup` instances as values, the attribute can be
        *set* in several ways, as the example shows.

        Example
        -------

        >>> gradebook.grading_groups = {
        ...     # list of assignments, followed by group weight. assignment weights
        ...     # are inferred to be proportional to points possible
        ...     "homeworks": (['hw 01', 'hw 02', 'hw 03'], 0.25),

        ...     # dictionary of assignment weights, followed by group weight.
        ...     "labs": ({"lab 01": .25, "lab 02": .75}, 0.25),
        ...
        ...     # callable that produces assignment names or an assignment weight dict.
        ...     "projects": (func, 0.25),
        ...
        ...     # group weight only. the key is interpreted as an assignment name,
        ...     # and an assignment group consisting only of that assignment is
        ...     # created.
        ...     "exam": 0.25
        ... }

    scale : Optional[OrderedMapping]
        An ordered mapping from letter grades to score thresholds used to
        determine overall letter grades. If not provided,
        :mod:`gradelib.scales.DEFAULT_SCALE` is used.

    """

    _kwarg_names = [
        "points_earned",
        "points_possible",
        "lateness",
        "dropped",
        "notes",
        "grading_groups",
        "scale",
        "opts",
    ]

    def __init__(
        self,
        points_earned,
        points_possible,
        lateness=None,
        dropped=None,
        notes=None,
        grading_groups=None,
        scale=None,
        opts=None,
    ):
        self.opts = opts if opts is not None else GradebookOptions()
        self.points_earned = _cast_index(points_earned)
        self.points_possible = points_possible
        self.lateness = (
            lateness if lateness is not None else _empty_lateness_like(points_earned)
        )
        self.dropped = (
            dropped if dropped is not None else _empty_mask_like(points_earned)
        )
        self.notes = {} if notes is None else notes
        self.grading_groups = {} if grading_groups is None else grading_groups
        self.scale = DEFAULT_SCALE if scale is None else scale

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} object with "
            f"{len(self.assignments)} assignments "
            f"and {len(self.pids)} students>"
        )

    # properties: assignments, students, lates -----------------------------------------

    @property
    def assignments(self) -> Assignments:
        """All assignments in the gradebook.

        This is a dynamically-computed property; it should not be modified.

        Returns
        -------
        Assignments

        """
        return Assignments(self.points_earned.columns)

    @property
    def pids(self) -> set[str]:
        """All student PIDs.

        This is a dynamically-computed property; it should not be modified.

        Returns
        -------
        set

        """
        return set(self.points_earned.index)

    @property
    def students(self) -> Students:
        """All students as Student objects.

        Returned in the order they appear in the indices of the `points_earned`
        attribute.

        This is a dynamically-computed property; it should not be modified.

        Returns
        -------
        Students

        """
        return Students([s for s in self.points_earned.index])

    @property
    def late(self) -> pd.DataFrame:
        """A boolean dataframe telling which assignments were turned in late.

        Will have the same index and columns as the `points_earned` attribute.

        This is computed from the :attr:`lateness` attribute using the
        :attr:`GradebookOptions.lateness_fudge` option. If the lateness is less than the
        lateness fudge, the assignment is considered on-time; otherwise, it is
        considered late. This can be useful to work around grade sources whose
        reported lateness is not always reliable, such as Gradescope.

        This is a dynamically-computed property; it should not be modified.

        """
        fudge = self.opts.lateness_fudge
        return self.lateness > pd.Timedelta(fudge, unit="s")

    # properties: groups ---------------------------------------------------------------

    @property
    def grading_groups(self) -> dict[str, GradingGroup]:
        return dict(self._groups)

    @grading_groups.setter
    def grading_groups(self, value):
        """.grading_groups setter that accepts several difference convenience formats.

        The value should be a dict mapping group names to *group definitions*. A group
        definition can be any of the following:

            - A single float representing a group weight. In this case, the group name
              is treated as an assignment name.

        """
        if not isinstance(value, dict):
            raise ValueError("Groups must be provided as a dictionary.")

        def _make_group(g, name):
            if isinstance(g, GradingGroup):
                return g

            if isinstance(g, (float, int)):
                # should be a number. this form defines a group with a single assignment
                assignment_weights = [name]
                group_weight = float(g)
            elif isinstance(g, collections.abc.Collection) and len(g) == 2:
                assignment_weights = g[0]
                group_weight = g[1]
            else:
                raise TypeError("Unexpected type for groups.")

            if callable(assignment_weights):
                assignment_weights = assignment_weights(self.assignments)

            if not isinstance(assignment_weights, dict):
                # an iterable of assignments that we need to turn into a dict
                total_points_possible = sum(
                    self.points_possible[a] for a in assignment_weights
                )
                assignment_weights = {
                    a: self.points_possible[a] / total_points_possible
                    for a in assignment_weights
                }

            return GradingGroup(assignment_weights, group_weight)

        new_groups = {name: _make_group(g, name) for name, g in value.items()}

        if new_groups:
            total_weight = sum(g.group_weight for g in new_groups.values())
            if self.opts.allow_extra_credit:
                if total_weight < 1:
                    raise ValueError('Group weights must sum to >= 1.')
            elif not math.isclose(total_weight, 1):
                raise ValueError(
                        "Group weights must sum to one unless the 'allow_extra_credit' "
                        "option is enabled."
                )

        self._groups = new_groups

    # properties: weights and values ---------------------------------------------------

    @property
    def weight(self) -> pd.DataFrame:
        """A table of assignment weights relative to their assignment group.

        If :attr:`grading_groups` is set, this computes a table of the same
        size as :attr:`points_earned` containing for each student and
        assignment, the weight of that assignment relative to the assignment
        group.

        If an assignment is not in an assignment group, the weight for that
        assignment is `NaN`. If no grading groups have been defined, all
        weights are `Nan`.

        If the assignment is dropped for that student, the weight is zero.
        If *all* assignments in a group have been dropped, `ValueError` is
        raised.

        Note that this is **not** the overall weight towards to the overall
        score. That is computed in :attr:`overall_weight`.

        This is a dynamically-computed property; it should not be modified.

        Raises
        ------
        ValueError
            If all assignments in a group have been dropped for a student,
            the weights are undefined.

        """
        result = self.points_possible / self._by_group_to_by_assignment(
            self._group_points_possible_after_drops
        )

        for group_name, group in self.grading_groups.items():
            if isinstance(group.assignment_weights, dict):
                weights = pd.Series(group.assignment_weights)
                weights = self._everyone_to_per_student(weights)
                weights = weights * ~self.dropped[list(group.assignment_weights)]
                weights = (weights.T / weights.sum(axis=1)).T
                result.loc[:, list(group.assignment_weights)] = weights

        return result * (~self.dropped)

    @property
    def overall_weight(self) -> pd.DataFrame:
        """A table of assignment weights relative to all other assignments.

        If :attr:`grading_groups` is set, this computes a table of the same
        size as :attr:`points_earned` containing for each student and
        assignment, the overall weight of that assignment relative to all other
        assignments.

        If an assignment is not in an assignment group, the weight for that
        assignment is `NaN`. If no grading groups have been defined, all
        weights are `Nan`.

        If the assignment is dropped for that student, the weight is zero. If
        *all* assignments in a group have been dropped, `ValueError` is raised.

        Note that this is **not** the weight of the assignment relative to the
        total weight of the assignment group it is in. That is That is computed
        in :attr:`weight`.

        This is a dynamically-computed property; it should not be modified.

        Raises
        ------
        ValueError
            If all assignments in a group have been dropped for a student,
            the weights are undefined.

        """

        group_weight = pd.Series(
            {
                group_name: assignment_group.group_weight
                for group_name, assignment_group in self.grading_groups.items()
            },
            dtype=float,
        )
        return self.weight * self._by_group_to_by_assignment(group_weight)

    @property
    def value(self) -> pd.DataFrame:
        """A table containing the value of each assignment for each student.

        This produces a table of the same size as :attr:`points_earned` where
        each entry contains the value of an assignment for a given student. The
        "value" of an assignment is the amount that it contributes to the
        student's overall score in the class. In short, it is the product of
        that assignment's score with its overall weight.

        If :attr:`grading_groups` is not set, all entries are `NaN`.

        The total of a student's assignment values equals their score in the
        class.

        This is a dynamically-computed property; it should not be modified.

        Raises
        ------
        ValueError
            If all assignments in a group have been dropped for a student,
            the weights are undefined.

        """
        return (self.points_earned / self.points_possible) * self.overall_weight

    # properties: scores ---------------------------------------------------------------

    @property
    def _group_points_possible_after_drops(self) -> pd.DataFrame:
        """A table of the number of points possible in an assignment group, after drops.

        Produces a table with one row per student, and one column per assignment group,
        containing the number of points possible in that group after dropped assignments
        have been removed.

        This is a dynamically-computed property; it should not be modified.

        Raises
        ------
        ValueError
            If all assignments in an assignment group have been dropped for a student.

        """
        result = {}
        for group_name, group in self.grading_groups.items():
            possible = pd.DataFrame(
                np.tile(
                    self.points_possible[list(group.assignment_weights)],
                    (self.points_earned.shape[0], 1),
                ),
                index=self.students,
                columns=list(group.assignment_weights),
            )

            possible[self.dropped[list(group.assignment_weights)]] = 0
            possible = possible.sum(axis=1)

            if (possible == 0).any():
                problematic_pids = list(possible.index[possible == 0])
                raise ValueError(
                    f"All assignments are dropped for {problematic_pids} in group '{group_name}'."
                )

            result[group_name] = possible

        return pd.DataFrame(result, index=self.students)

    @property
    def grading_group_scores(self) -> pd.DataFrame:
        """A table of the scores earned in each assignment group.

        Produces a DataFrame with a row for each student and a column for each
        assignment group in which each entry is the student's score within that
        assignment group.

        This takes into account dropped assignments.

        If :attr:`grading_groups` has not yet been set, all entries are `NaN`.

        This is a dynamically-computed property; it should not be modified.

        """
        group_values = pd.DataFrame(
            {
                group_name: self.value[list(group.assignment_weights)].sum(axis=1)
                for group_name, group in self.grading_groups.items()
            }
        )
        group_weight = pd.Series(
            {
                group_name: group.group_weight
                for group_name, group in self.grading_groups.items()
            }
        )
        return group_values / group_weight

    def _by_group_to_by_assignment(self, by_group):
        """Creates an (students, assignments) DataFrame by tiling.

        Parameters
        ----------
        by_group
            Can be a Series or a DataFrame. If it is a DataFrame, it should
            have group names as columns and students in the index. Each
            column is "expanded" by creating a new column for each
            assignment in the group whose value is a copy of the group's
            column in the input. If a Series, it should have group names as
            its index. The Series is first converted to a (student, groups)
            dataframe by tiling, then to a (student, assignments) dataframe
            using the above procedure.

        Returns
        -------
        DataFrame

        """

        def _get_group_by_name(name):
            for group_name, group in self.grading_groups.items():
                if group_name == name:
                    return group

        def _convert_df(df):
            new_columns = {}
            for group_name in df.columns:
                for assignment in _get_group_by_name(group_name).assignment_weights:
                    new_columns[assignment] = df[group_name]
            return pd.DataFrame(new_columns, index=self.students)

        def _convert_series(s):
            new_columns = {}
            for group_name in s.index:
                new_columns[group_name] = np.repeat(
                    s[group_name], len(self.points_earned)
                )
            df = pd.DataFrame(new_columns, index=self.students)
            return _convert_df(df)

        if isinstance(by_group, pd.Series):
            return _convert_series(by_group)
        else:
            return _convert_df(by_group)

    def _everyone_to_per_student(self, s):
        """Converts a (groups,) or (assignments,) Series to a (students, *) DataFrame."""
        return pd.DataFrame(
            np.tile(s.values, (len(self.points_earned), 1)),
            columns=s.index,
            index=self.students,
        )

    @property
    def score(self) -> pd.DataFrame:
        """A table of scores on each assignment.

        Produces a DataFrame with a row for each student and a column for each assignment
        containing the number of points earned on that assignment as a proportion of
        the number of points possible on that assignment.

        Does not take into account drops.

        This is a dynamically-computed property; it should not be modified.

        """
        return self.points_earned / self.points_possible

    @property
    def overall_score(self) -> pd.Series:
        """A series containing the overall score earned by each student.

        A pandas Series with an entry for each student in the Gradebook. The
        index is the same as the series returned by the :attr:`students`
        attribute. Each entry is the overall score in the class, taking drops
        into account.

        This is a dynamically-computed property; it should not be modified.

        Raises
        ------
        ValueError
            If :attr:`grading_groups` has not yet been set.

        """
        if not self.grading_groups:
            raise ValueError(
                "Grading groups should be set before calculating letter grades."
            )

        return self.value.sum(axis=1)

    # properties: letter grades --------------------------------------------------------

    @property
    def letter_grades(self) -> pd.Series:
        """A series containing the letter grade earned by each student.

        A pandas Series with an entry for each student in the Gradebook. The
        index is the same as the series returned by the :attr:`students`
        attribute. Each entry is the letter grade the class, taking drops into
        account, and calculated using the value of the :attr:`scale` attribute.

        This is a dynamically-computed property; it should not be modified.

        Raises
        ------
        ValueError
            If :attr:`grading_groups` has not yet been set.

        """
        if not self.grading_groups:
            raise ValueError(
                "Grading groups should be set before calculating letter grades."
            )

        return map_scores_to_letter_grades(self.overall_score, scale=self.scale)

    # copying / replacing --------------------------------------------------------------

    def _replace(self, **kwargs):

        extra = set(kwargs.keys()) - set(self._kwarg_names)
        assert not extra, f"Invalid kwargs provided: {extra}"

        def _copy(obj):
            if hasattr(obj, "copy"):
                return obj.copy()
            else:
                return copy.deepcopy(obj)

        new_kwargs = {}
        for kwarg_name in self._kwarg_names:
            if kwarg_name in kwargs:
                new_kwargs[kwarg_name] = kwargs[kwarg_name]
            else:
                new_kwargs[kwarg_name] = _copy(getattr(self, kwarg_name))

        return self.__class__(**new_kwargs)

    def copy(self):
        """Copy the gradebook.

        Returns
        -------
        Gradebook
            A new gradebook with all attributes copied.

        """
        return self._replace()

    # adding/removing assignments ------------------------------------------------------

    def add_assignment(
        self,
        name: str,
        points_earned: pd.Series,
        points_possible: pd.Series,
        lateness: typing.Optional[pd.Series] = None,
        dropped: typing.Optional[pd.Series] = None,
    ):
        """Adds a single assignment to the gradebook, mutating it.

        Usually gradebooks do not need to have individual assignments added to them.
        Instead, gradebooks are read from Canvas, Gradescope, etc. In some instances,
        though, it can be useful to manually add an assignment to a gradebook -- this
        method makes it easy to do so.

        Parameters
        ----------
        name : str
            The name of the new assignment. Must be unique.
        points_earned : Series[float]
            A Series of points earned by each student.
        points_possible : float
            The maximum number of points possible on the assignment.
        lateness : Series[pd.Timedelta]
            How late each student turned in the assignment late. Default: all
            zero seconds.
        dropped : Series[bool]
            Whether the assignment should be dropped for any given student.
            Default: all False.

        Raises
        ------
        ValueError
            If an assignment with the given name already exists, or if grades for a student
            are missing / grades for an unknown student are provided.

        """
        if name in self.assignments:
            raise ValueError(f'An assignment with the name "{name}" already exists.')

        if lateness is None:
            lateness = pd.to_timedelta(pd.Series(0, index=self.students), unit="s")

        if dropped is None:
            dropped = pd.Series(False, index=self.students)

        def _match_pids(pids, where):
            """Ensure that pids match."""
            theirs = set(pids)
            ours = set(self.pids)
            if theirs - ours:
                raise ValueError(f'Unknown pids {theirs - ours} provided in "{where}".')
            if ours - theirs:
                raise ValueError(f'"{where}" is missing PIDs: {ours - theirs}')

        _match_pids(points_earned.index, "points")
        _match_pids(lateness.index, "late")
        _match_pids(dropped.index, "dropped")

        self.points_earned[name] = points_earned
        self.points_possible[name] = points_possible
        self.lateness[name] = lateness
        self.dropped[name] = dropped

    def restrict_to_assignments(self, assignments: AssignmentSelector):
        """Restrict the gradebook to only the supplied assignments.

        If the :attr:`grading_groups` attribute been set, it is reset to
        ``{}`` by this operation.

        Parameters
        ----------
        assignments : AssignmentSelector
            A collection of assignment names.

        Raises
        ------
        KeyError
            If an assignment was specified that was not in the gradebook.

        """
        if callable(assignments):
            assignments = assignments(self.assignments)
        else:
            assignments = list(assignments)
        extras = set(assignments) - set(self.assignments)
        if extras:
            raise KeyError(f"These assignments were not in the gradebook: {extras}.")

        self.points_earned = self.points_earned.loc[:, assignments]
        self.points_possible = self.points_possible[assignments]
        self.lateness = self.lateness.loc[:, assignments]
        self.dropped = self.dropped.loc[:, assignments]

        self.grading_groups = {}

    def remove_assignments(self, assignments: AssignmentSelector):
        """Removes assignments, mutating the gradebook.

        If the :attr:`grading_groups` attribute been set, it is reset to
        ``{}`` by this operation.

        Parameters
        ----------
        assignments : AssignmentSelector
            A collection of assignments names that will be removed.

        Raises
        ------
        KeyError
            If an assignment was specified that was not in the gradebook.

        """
        # TODO: preserve order better
        if callable(assignments):
            assignments = assignments(self.assignments)
        else:
            assignments = list(assignments)
        extras = set(assignments) - set(self.assignments)
        if extras:
            raise KeyError(f"These assignments were not in the gradebook: {extras}.")

        return self.restrict_to_assignments(set(self.assignments) - set(assignments))

    def rename_assignments(self, mapping: typing.Mapping[str, str]):
        """Renames assignments.

        If the :attr:`grading_groups` attribute been set, it is reset to
        ``{}`` by this operation.

        Parameters
        ----------
        mapping : dict[str, str]
            A mapping from existing column names to new names.

        Raises
        ------
        ValueError
            If a new name clashes with an existing name.

        """
        resulting_names = (set(self.assignments) - mapping.keys()) | set(
            mapping.values()
        )
        if len(resulting_names) != len(self.assignments):
            raise ValueError("Name clashes in renamed assignments.")

        self.points_earned.rename(columns=mapping, inplace=True)
        self.points_possible.rename(index=mapping, inplace=True)
        self.lateness.rename(columns=mapping, inplace=True)
        self.dropped.rename(columns=mapping, inplace=True)

    # adding/removing students ---------------------------------------------------------

    def restrict_to_students(self, to: typing.Collection[str]):
        """Restrict the gradebook to only the supplied PIDs.

        Parameters
        ----------
        to : Collection[str]
            A collection of PIDs. For instance, from the final course roster.

        Raises
        ------
        KeyError
            If a PID was specified that is not in the gradebook.

        """
        pids = list(to)
        extras = set(pids) - set(self.pids)
        if extras:
            raise KeyError(f"These PIDs were not in the gradebook: {extras}.")

        self.points_earned = self.points_earned.loc[pids]
        self.lateness = self.lateness.loc[pids]
        self.dropped = self.dropped.loc[pids]

    # notes ----------------------------------------------------------------------------

    def add_note(self, pid: str, channel: str, message: str):
        """Convenience method for adding a note.

        Mutates the gradebook.

        Parameters
        ----------
        pid : str
            The pid of the student for which the note should be added.

        channel : str
            The channel that the note should be added to. Valid channels are:
                - lates
                - drops
                - misc

        message : str
            The note's message.

        """
        if pid not in self.notes:
            self.notes[pid] = {}

        if channel not in self.notes[pid]:
            self.notes[pid][channel] = []

        self.notes[pid][channel].append(message)

    # apply ----------------------------------------------------------------------------

    def apply(
        self,
        transformations: typing.Union[
            typing.Sequence[typing.Callable], typing.Callable
        ],
    ) -> "Gradebook":
        """Apply transformation(s) to the gradebook.

        A transformation is a callable that takes in a gradebook object and
        returns a gradebook object. No assumption is made as to whether the
        transformation mutates the input or produces a copy (it could return
        the instance given as input, for example).

        If a sequence of transformations is provided, the output of a
        transformation is used as the input to the next transformation in the
        sequence.

        The gradebook is copied before handing it to the first transformation,
        so self is guaranteed to be unmodified. This allows transformations
        which mutate for performance reasons while still guaranteeing that the
        overall application does not mutate this gradebook.

        Parameters
        ----------
        transformations : Sequence[Callable] or Callable
            Either a single gradebook transformation or a sequence of
            transformations.

        Returns
        -------
        Gradebook
            The result of the last transformation in the sequence.

        """
        try:
            transformations = list(transformations)
        except TypeError:
            transformations = [transformations]

        result = self.copy()
        for transformation in transformations:
            result = transformation(result)

        return result
