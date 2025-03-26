"""A type for managing a collection of grades."""

import copy
import dataclasses
import math
from typing import Sequence, Collection, Mapping, Union, Tuple, Optional
from numbers import Real

from ..scales import DEFAULT_SCALE, map_scores_to_letter_grades
from .._util import empty_mask_like, ensure_df, ensure_series
from ._student import Student, Students
from ._assignments import Assignments

import numpy as np
import pandas as pd


# private helper functions =============================================================


def _empty_lateness_like(table: pd.DataFrame) -> pd.DataFrame:
    """Given a dataframe, create another like it with every entry a timedelta of 0."""
    empty = table.copy()
    empty.iloc[:, :] = 0
    for column in empty.columns:
        empty[column] = pd.to_timedelta(empty[column], unit="s")  # pyright: ignore
    return empty


def _cast_index_to_student_objects(table: pd.DataFrame) -> pd.DataFrame:
    """Ensure that the dataframe index contains Student objects."""

    def _cast(x):
        if isinstance(x, Student):
            return x
        else:
            return Student(x)

    table.index = [_cast(x) for x in table.index]
    return table


def _concatenate_notes(
    gradebooks: Sequence["Gradebook"],
) -> dict[Student, dict[str, list[str]]]:
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


def _combine_if_equal(gradebooks: Collection["Gradebook"], attr: str):
    """Checks that the attribute is the same in all gradebooks.

    If it is, the common attribute is returned. Otherwise, a `ValueError` is raised.

    Parameters
    ----------
    gradebooks : Collection[Gradebook]
        The gradebooks to check.
    attr : str
        The attribute to check.

    Returns
    -------
    object
        The value of the attribute.

    Raises
    ------
    ValueError
        If the attribute is not the same in all gradebooks.

    """
    obj = None
    for gradebook in gradebooks:
        if obj is None:
            obj = getattr(gradebook, attr)
        else:
            if getattr(gradebook, attr) != obj:
                raise ValueError("Objects do not match in all gradebooks.")

    return obj


def _copy_notes(
    notes: Mapping[Student, Mapping[str, Sequence[str]]],
) -> dict[Student, dict[str, list[str]]]:
    """Copy a mapping containing notes into a dictionary."""
    result = {}
    for outer_key, outer_value in notes.items():
        result[outer_key] = {k: list(v) for k, v in outer_value.items()}
    return result


def _coerce_extra_credit_to_float(v: Union[float, "ExtraCredit"]) -> float:
    """Converts an ExtraCredit object to a float."""
    if isinstance(v, ExtraCredit):
        return v.percentage
    return v


# public functions =====================================================================


def combine_gradebooks(
    gradebooks: Collection["Gradebook"],
    restrict_to_students: Optional[Collection[Union[str, Student]]] = None,
) -> "Gradebook":
    """Create a new :class:`Gradebook` by safely combining existing gradebooks.

    The gradebooks being combined must all have the same students, and an
    assignment name cannot appear in more than one gradebook. If either of
    these conditions are violated, a `ValueError` is raised.

    The new gradebook's grading groups are reset; there are no groups.

    If the scales are the same in each gradebook, the new gradebook's scale is
    set accordingly. If they are different, a ``ValueError`` is raised. The same
    is true for the ``options`` attribute.

    Parameters
    ----------
    gradebooks : Collection[Gradebook]
        The gradebooks to combine.
    restrict_to_students : Optional[Collection[Union[str, Student]]]
        If provided, each input gradebook will be restricted to the
        Students/PIDs given before attempting to combine them. This is a
        convenience option, and it simply calls
        :meth:`Gradebook.restrict_to_students` on each of the inputs.
        Default: None

    Returns
    -------
    Gradebook
        A gradebook combining all of the input gradebooks.

    Raises
    ------
    ValueError
        If the PID indices of gradebooks do not match; if there is a duplicate
        assignment name; the options do not match; the scales do not match.

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
    def concatenate_table_attr(a: str, axis=1):
        """Create a DF/Series by combining the same attribute across gradebooks."""
        all_tables = [getattr(gb, a) for gb in gradebooks]
        return pd.concat(all_tables, axis=axis)

    return Gradebook(
        points_earned=ensure_df(concatenate_table_attr("points_earned")),
        points_possible=ensure_series(
            concatenate_table_attr("points_possible", axis=0)
        ),
        lateness=ensure_df(concatenate_table_attr("lateness")),
        dropped=ensure_df(concatenate_table_attr("dropped")),
        notes=_concatenate_notes(gradebooks),
        grading_groups={},
        options=_combine_if_equal(gradebooks, "options"),
        scale=_combine_if_equal(gradebooks, "scale"),
    )


# public classes =======================================================================


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

    """

    lateness_fudge: int = 5 * 60


# GradingGroup --------------------------------------------------------------------------------


class ExtraCredit:
    """Represents extra credit in a grading group.

    Parameters
    ----------
    percentage : float
        The percentage of extra credit to give. For example, if this is 0.1,
        then the group will be worth 10% (on top of the normal 100%).

    """

    def __init__(self, percentage: float):
        self.percentage = percentage

    def __repr__(self):
        return f"ExtraCredit({self.percentage!r})"


class GradingGroup:
    """Represents a logical group of assignments and their weights.

    Attributes
    ----------
    assignment_weights: Mapping[str, float | ExtraCredit]
        A dictionary mapping assignment names (strings) to their weight within the group
        (as a float between 0 and 1, or as an instance of :class:`ExtraCredit`). The
        weights of regular (non-extra credit) assignments should add to one.
    group_weight: float | ExtraCredit
        The weight of the group in the overall grade calculation. This should be a
        float between 0 and 1, or an instance of :class:`ExtraCredit`.
    cap_total_score_at_100_percent : bool
        If True, the total score for the group is capped at 100%. Default: False.

    Raises
    ------
    ValueError
        If the assignment weights are not between 0 and 1, they do not add to
        one, or if the group weight is not between 0 and 1.

    """

    _attrs = [
        "assignment_weights",
        "group_weight",
        "cap_total_score_at_100_percent",
    ]

    def __init__(
        self,
        assignment_weights: Mapping[str, float],
        group_weight: float,
        cap_total_score_at_100_percent: bool = False,
    ):
        self.assignment_weights = assignment_weights
        self.group_weight = group_weight
        self.cap_total_score_at_100_percent = cap_total_score_at_100_percent

        self.validate()

    @classmethod
    def with_equal_weights(
        cls,
        assignments: Collection[str],
        group_weight: float,
        cap_total_score_at_100_percent: bool = False,
    ) -> "GradingGroup":
        """Create a grading group in which each assignment is given equal weight.

        Parameters
        ----------
        assignments: Collection[str]
            The assignments to include in the group.
        group_weight: float
            The overall weight of the group.
        cap_total_score_at_100_percent: bool
            If True, the total score for the group is capped at 100%. Default: False.

        Returns
        -------
        GradingGroup

        Example
        -------
        .. testsetup:: with_equal_weights

            import pandas as pd
            import gradelib
            from gradelib import GradingGroup
            import numpy as np

            students = ["Alice", "Barack", "Charlie"]
            assignments = ["homework 01", "homework 02", "lab 01"]
            points_earned = pd.DataFrame(
                [[10, np.nan, np.nan], [np.nan, 10, np.nan], [np.nan, np.nan, 10]],
                index=students, columns=assignments
            )
            points_possible = pd.Series([10, 10, 10], index=assignments)
            gradebook = gradelib.Gradebook(points_earned, points_possible)

        .. doctest:: with_equal_weights

            >>> group = GradingGroup.with_equal_weights(['foo', 'bar', 'baz', 'quux'], 0.5)
            >>> group.assignment_weights
            {'foo': 0.25, 'bar': 0.25, 'baz': 0.25, 'quux': 0.25}

        """
        n = len(assignments)
        return cls(
            {a: 1 / n for a in assignments},
            group_weight=group_weight,
            cap_total_score_at_100_percent=cap_total_score_at_100_percent,
        )

    @classmethod
    def with_proportional_weights(
        cls,
        gb: "Gradebook",
        assignments: Collection[str],
        group_weight: float,
        cap_total_score_at_100_percent: bool = False,
    ) -> "GradingGroup":
        """Create a grading group in which each assignment is weighed proportionally.

        An assignment's weight within the group is proportional to the number of
        points possible for that assignment.

        Parameters
        ----------
        gb : Gradebook
            The gradebook containing the assignments.
        assignments: Collection[str]
            The assignments to include in the group.
        group_weight: float
            The overall weight of the group.

        Returns
        -------
        GradingGroup

        Example
        -------
        .. testsetup:: with_proportional_weights

            import pandas as pd
            import gradelib
            from gradelib import GradingGroup
            import numpy as np

            students = ["Alice", "Barack", "Charlie"]

            assignments = ["homework 01", "homework 02", "lab 01"]
            points_earned = pd.DataFrame(
                [[10, np.nan, np.nan], [np.nan, 10, np.nan], [np.nan, np.nan, 10]],
                index=students, columns=assignments
            )
            points_possible = pd.Series([15, 45, 30], index=assignments)
            gradebook = gradelib.Gradebook(points_earned, points_possible)

        .. doctest:: with_proportional_weights

            >>> group = GradingGroup.with_proportional_weights(
            ...     gradebook, ['homework 01', 'homework 02'], 0.5
            ... )
            >>> group.assignment_weights
            {'homework 01': 0.25, 'homework 02': 0.75}

        """
        total_points_possible = gb.points_possible.loc[assignments].sum()

        assignment_weights = {
            a: gb.points_possible[a] / total_points_possible for a in assignments
        }

        return cls(
            assignment_weights,
            group_weight=group_weight,
            cap_total_score_at_100_percent=cap_total_score_at_100_percent,
        )

    def with_extra_credit_assignments(
        self, extra_credit: Mapping[str, float]
    ) -> "GradingGroup":
        """Add extra credit assignments to the grading group.

        This creates a new grading group with the same assignments as the original
        group, but with extra credit assignments added.

        Parameters
        ----------
        extra_credit : Mapping[str, float]
            A dictionary mapping assignment names to their weight within the group
            (as a float between 0 and 1).

        Returns
        -------
        GradingGroup

        """
        new_assignment_weights = copy.deepcopy(self.assignment_weights)

        for extra_credit_assignment, weight in extra_credit.items():
            if extra_credit_assignment in new_assignment_weights:
                raise ValueError(
                    f"Assignment '{extra_credit_assignment}' is already in the group."
                )

            new_assignment_weights[extra_credit_assignment] = ExtraCredit(weight)

        return GradingGroup(
            new_assignment_weights,
            group_weight=self.group_weight,
            cap_total_score_at_100_percent=self.cap_total_score_at_100_percent,
        )

    def __repr__(self):
        return (
            f"GradingGroup(assignment_weights={self.assignment_weights!r}, "
            f"group_weight={self.group_weight!r})"
        )

    @property
    def assignments(self) -> Assignments:
        """The assignments in the group."""
        return Assignments(list(self.assignment_weights))

    def __eq__(self, other):
        return all(getattr(self, attr) == getattr(other, attr) for attr in self._attrs)

    @property
    def regular_assignment_weights(self) -> dict[str, float]:
        """Returns a dictionary of the regular (non-extra credit) assignment weights."""
        return {
            k: v
            for k, v in self.assignment_weights.items()
            if not isinstance(v, ExtraCredit)
        }

    @property
    def extra_credit_assignment_weights(self) -> dict[str, float]:
        """Returns a dictionary of the extra credit assignment weights."""
        return {
            k: v.percentage
            for k, v in self.assignment_weights.items()
            if isinstance(v, ExtraCredit)
        }

    def validate(self):
        """Validate the grading group.

        Makes sure that:

            - The assignment weights are between 0 and 1.
            - The regular assignment weights sum to one.
            - The group weight is between 0 and 1.
            - The group doesn't contain only extra credit assignments.

        Raises a `ValueError` if any of these conditions are not met.

        """
        if not self.regular_assignment_weights:
            raise ValueError("Must have at least one regular assignment.")

        if not math.isclose(sum(self.regular_assignment_weights.values()), 1):
            raise ValueError("Regular assignment weights must sum to one.")

        if not all(
            0 <= _coerce_extra_credit_to_float(w) <= 1
            for w in self.assignment_weights.values()
        ):
            raise ValueError("Assignment weights must be between 0 and 1.")

        if not 0 <= _coerce_extra_credit_to_float(self.group_weight) <= 1:
            raise ValueError("Group weight must be between 0 and 1.")


# type alias for the multiple valid ways to specify a grading group
GradingGroupDefinition = Union[float, Tuple[Mapping[str, float], float], GradingGroup]


# Gradebook ============================================================================


class Gradebook:
    """Stores the grades for a class.

    Typically a Gradebook is not created manually, but is instead produced by
    reading grades exported from Gradescope or Canvas, using
    :func:`gradelib.io.gradescope.read` or :func:`gradelib.io.canvas.read`.

    Parameters
    ----------
    points_earned : pandas.DataFrame
        A dataframe with one row per student, and one column for each
        assignment. Each entry should be the raw number of points earned by the
        student on the given assignment (or `NaN` if the student did not turn
        in the assignment). The index of the dataframe should consist of
        :class:`Student` objects.
    points_possible : pandas.Series
        A series containing the maximum number of points possible for each
        assignment. The index of the series should match the columns of the
        `points_earned` dataframe.
    lateness : Optional[pandas.DataFrame]
        A dataframe of `pd.Timedelta` objects with the same columns/index as
        `points_earned`. An entry in the dataframe records how late a student
        turned in the assignment. If `None` is passed, a dataframe of zero
        second timedeltas is used by default, effectively indicating that no
        assignments were late.
    dropped : Optional[pandas.DataFrame]
        A Boolean dataframe with the same columns/index as `points_earned`. An
        entry that is `True` indicates that the assignment should be dropped.
        If `None` is passed, a dataframe of all `False` is used by default.
    notes : Optional[Mapping[Student, Mapping[str, Sequence[str]]]]
        A nested dictionary of notes, possibly used by report generating code.
        The keys of the outer dictionary should be :class:`Student` objects,
        and the values should be dictionaries. The keys of the inner dictionary
        should specify a note channel, and can be either "late", "drop", or
        "misc"; these are signals to reporting code that help determine where
        to display notes. The values of the inner dictionary should be
        sequences of strings, each one a message.
    options : Optional[GradebookOptions]
        Options controlling the behavior of the Gradebook. If not provided,
        default options are used.
    grading_groups : Mapping[str, GradingGroup]
        A mapping from assignment group names (strings) to :class:`GradingGroup`
        objects representing a group of assignments. The default is simply ``{}``.

        To prevent unintentional errors, the grading groups must be set before
        accessing summative attributes, such as :attr:`overall_score`.

        While the dictionary returned by this attribute has
        :class:`GradingGroup` instances as values, the attribute can be
        *set* in several ways. See the documentation for the
        setter for more details.
    scale : Optional[Mapping]
        An ordered mapping from letter grades to score thresholds used to
        determine overall letter grades. If not provided,
        :mod:`gradelib.scales.DEFAULT_SCALE` is used.

    Attributes
    ----------
    notes : dict[Student, dict[str, list[str]]]
        A nested dictionary of notes, possibly used by report generating code.
    options : GradebookOptions
        Options controlling the behavior of the Gradebook.
    scale : dict
        An ordered mapping from letter grades to score thresholds used to
        determine overall letter grades.

    """

    _kwarg_names = [
        "points_earned",
        "points_possible",
        "lateness",
        "dropped",
        "notes",
        "grading_groups",
        "scale",
        "options",
    ]

    def __init__(
        self,
        points_earned: pd.DataFrame,
        points_possible: pd.Series,
        lateness: Optional[pd.DataFrame] = None,
        dropped: Optional[pd.DataFrame] = None,
        notes: Optional[Mapping[Student, Mapping[str, Sequence[str]]]] = None,
        grading_groups: Optional[Mapping[str, GradingGroupDefinition]] = None,
        scale: Optional[Mapping] = None,
        options: Optional[GradebookOptions] = None,
    ):
        self.options = options if options is not None else GradebookOptions()
        self.points_earned = _cast_index_to_student_objects(points_earned).astype(float)
        self.points_possible = points_possible.astype(float)
        self.lateness = (
            lateness if lateness is not None else _empty_lateness_like(points_earned)
        )
        self.dropped = (
            dropped if dropped is not None else empty_mask_like(points_earned)
        )
        self.notes = {} if notes is None else _copy_notes(notes)
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

        This is a derived attribute; it should not be modified.

        Returns
        -------
        Assignments

        """
        return Assignments(list(self.points_earned.columns))

    @property
    def pids(self) -> set[str]:
        """All student PIDs.

        This is a derived attribute; it should not be modified.

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

        This is a derived attribute; it should not be modified.

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
        :attr:`GradebookOptions.lateness_fudge` option. If the lateness is less
        than the lateness fudge, the assignment is considered on-time;
        otherwise, it is considered late. This can be useful to work around
        grade sources whose reported lateness is not always reliable, such as
        Gradescope.

        This is a derived attribute; it should not be modified.

        """
        fudge = self.options.lateness_fudge
        return self.lateness > pd.Timedelta(fudge, unit="s")

    # properties: groups ---------------------------------------------------------------

    @property
    def grading_groups(self) -> dict[str, GradingGroup]:
        """A grouping of assignments and their weight in the overall grade.

        This attribute should be set directly. The value should be a dict
        mapping group names to *grading group definitions*. A group definition
        can be either of the following:

            - A single number. In this case, the group name is treated as an
              assignment name.
            - A tuple of the form ``(assignments, group_weight)``, where ``assignments``
              is a dict mapping assignment names to weights.
            - A :class:`GradingGroup` instance.

        To normalize the weights of assignments (so that they are all weighed the same)
        use :meth:`GradingGroup.with_equal_weights`. To set the weights proportionally,
        use :meth:`GradingGroup.with_proportional_weights`.

        Example
        -------

        .. testsetup:: grading_groups

            import pandas as pd
            import gradelib
            import numpy as np

            students = ["Alice", "Barack", "Charlie"]
            assignments = ["hw 01", "hw 02", "hw 03", "lab 01", "lab 02", "exam"]
            points_earned = pd.DataFrame(
                np.random.randint(0, 10, size=(len(students), len(assignments))),
                index=students, columns=assignments
            )
            points_possible = pd.Series([10, 10, 10, 20, 15, 20], index=assignments)
            gradebook = gradelib.Gradebook(points_earned, points_possible)

        .. doctest:: grading_groups

            >>> gradebook.grading_groups = {
            ...     # dictionary of assignment weights, followed by group weight.
            ...     "labs": ({"lab 01": .25, "lab 02": .75}, 0.25),
            ...
            ...     # a single number. the key is interpreted as an assignment name,
            ...     # and an assignment group consisting only of that assignment is
            ...     # created.
            ...     "exam": 0.5,
            ...
            ...     # use equal weights for all assignments
            ...     "homework": gradelib.GradingGroup.with_equal_weights(["hw 01", "hw 02", "hw 03"], 0.25)
            ... }

        """
        return dict(self._groups)

    @grading_groups.setter
    def grading_groups(
        self,
        value: Mapping[str, GradingGroupDefinition],
    ):
        if not isinstance(value, dict):
            raise ValueError("Groups must be provided as a dictionary.")

        def _make_group(g: GradingGroupDefinition, name: str) -> GradingGroup:
            if isinstance(g, GradingGroup):
                # validate the grading group
                g.validate()
                return g
            if isinstance(g, Real):
                # should be a number. this form defines a group with a single assignment
                # whose weight within the group is 100%
                assignment_weights = {name: 1}
                group_weight = float(g)
            elif isinstance(g, ExtraCredit):
                assignment_weights = {name: 1}
                group_weight = g
            elif isinstance(g, tuple):
                if not isinstance(g[0], Mapping):
                    raise TypeError(
                        f"Invalid grading group definition: {g}. "
                        "When a grading group definition is a (Mapping, Number) tuple, "
                        "the first element must be a mapping from assignment names to "
                        "weights."
                    )
                if not all(isinstance(k, str) for k in g[0].keys()):
                    raise TypeError(
                        f"Invalid grading group definition: {g}. "
                        "When a grading group definition is a (Mapping, Number) tuple, "
                        "Assignment names in the mapping must be strings. "
                    )
                if not all(isinstance(v, Real) for v in g[0].values()):
                    raise TypeError(
                        f"Invalid grading group definition: {g}. "
                        "When a grading group definition is a (Mapping, Number) tuple, "
                        "Assignment weights in the mapping must be numbers. "
                    )

                assignment_weights = {
                    str(a_name): float(a_weight) for a_name, a_weight in g[0].items()
                }
                group_weight = float(g[1])
            else:
                raise TypeError("Unexpected type in grading group definition.")

            if not assignment_weights:
                raise ValueError(f'Grading group "{name}" is empty.')

            return GradingGroup(assignment_weights, group_weight)

        new_groups = {name: _make_group(g, name) for name, g in value.items()}

        if new_groups:

            def _coerce_extra_credit_to_zero(v: float | ExtraCredit) -> float:
                """Converts an ExtraCredit object to zero."""
                if isinstance(v, ExtraCredit):
                    return 0
                return v

            total_weight = sum(
                _coerce_extra_credit_to_zero(g.group_weight)
                for g in new_groups.values()
            )

            if not math.isclose(total_weight, 1):
                raise ValueError(
                    "Group weights must sum to one (excluding extra credit)."
                )

        self._groups = new_groups

    # properties: weights and values ---------------------------------------------------

    @property
    def weight_in_group(self) -> pd.DataFrame:
        """A table of assignment weights relative to their assignment group.

        If :attr:`grading_groups` is set, this computes a table of the same size as
        :attr:`points_earned` containing for each student and assignment, the weight of
        that assignment relative to the assignment group.

        If an assignment is not in an assignment group, the weight for that assignment
        is `NaN`. If no grading groups have been defined, all weights are `Nan`.

        If the assignment is dropped for that student, the weight is zero. If *all*
        assignments in a group have been dropped, `ValueError` is raised.

        An extra credit assignment (denoted by a weight wrapped in :class:`ExtraCredit`)
        has its weight converted to a float between 0 and 1, and is treated as a regular
        assignment, however, summing all of the weights in a group will add up to more
        than 1.

        Note that this is **not** the overall weight towards to the overall score. That
        is computed in :attr:`overall_weight`.

        This is a derived attribute; it should not be modified.

        Raises
        ------
        ValueError
            If all assignments in a group have been dropped for a student,
            the weights are undefined.

        """
        # the result is an (n_students, n_grading_groups) dataframe
        result = pd.DataFrame({}, index=pd.Index(self.students))

        def _check_if_all_dropped(group_name: str):
            """Checks if there are any students whose assignments are all dropped."""
            group = self.grading_groups[group_name]
            all_dropped = self.dropped[list(group.assignment_weights)].all(axis=1)
            assert isinstance(all_dropped, pd.Series)
            if all_dropped.any():
                problematic_pids = list(all_dropped.index[all_dropped])  # type: ignore
                raise ValueError(
                    f"All assignments are dropped for {problematic_pids} in group '{group_name}'."
                )

        def _grading_group_weights(group_name: str) -> pd.DataFrame:
            """Computes a table of weights for assignments in a single grading group.

            The result is an (n_students, n_assignments_in_group) dataframe.

            We do this per-student because different students have different dropped
            assignments, so each student has a different total weight for the group.

            """
            _check_if_all_dropped(group_name)

            assignments = list(group.assignment_weights)

            regular_assignments = list(group.regular_assignment_weights)
            extra_credit_assignments = list(group.extra_credit_assignment_weights)

            assignment_weights = {
                k: _coerce_extra_credit_to_float(v)
                for k, v in group.assignment_weights.items()
            }

            weights = pd.Series(assignment_weights)

            # make `weights` an (n_students, n_assignments_in_group) dataframe
            weights = self._everyone_to_per_student(weights)

            # compute a total weight for each student. This is a sum of all assignment
            # weights, excluding dropped assignments and extra credit assignments.
            # `total_weight` is a Series with one entry per student.
            total_weight = weights.copy()
            total_weight[extra_credit_assignments] = 0
            total_weight[self.dropped[assignments]] = 0
            total_weight = total_weight.sum(axis=1)

            # set weight of dropped assignments to zero
            weights = weights * ~self.dropped[assignments]

            # renormalize the weights so that they sum to one for each student. Only
            # do this for regular assignments! Extra credit assignments are not
            # renormalized.
            weights.loc[:, regular_assignments] = (
                weights.loc[:, regular_assignments].T / total_weight
            ).T

            return weights

        for group_name, group in self.grading_groups.items():
            result.loc[:, list(group.assignment_weights)] = _grading_group_weights(
                group_name
            )

        return result * (~self.dropped)

    @property
    def overall_weight(self) -> pd.DataFrame:
        """A table of assignment weights relative to all other assignments.

        Usually, an assignment's weight relative to all other assignments is the weight
        of its group times the weight of the assignment within the group.

        If :attr:`grading_groups` is set, this computes a table of the same size as
        :attr:`points_earned` containing for each student and assignment, the overall
        weight of that assignment relative to all other assignments.

        If an assignment is not in an assignment group, the weight for that assignment
        is `NaN`. If no grading groups have been defined, all weights are `Nan`.

        If the assignment is dropped for that student, the weight is zero. If *all*
        assignments in a group have been dropped, `ValueError` is raised.


        Note that this is **not** the weight of the assignment relative to the total
        weight of the assignment group it is in. That is computed in :attr:`weight`.

        This is a derived attribute; it should not be modified.

        Raises
        ------
        ValueError
            If all assignments in a group have been dropped for a student,
            the weights are undefined.

        """

        group_weight = self._by_grading_group_to_by_assignment(
            pd.Series(
                {
                    group_name: _coerce_extra_credit_to_float(
                        assignment_group.group_weight
                    )
                    for group_name, assignment_group in self.grading_groups.items()
                },
                dtype=float,
            )
        )
        return self.weight_in_group * group_weight

    @property
    def value(self) -> pd.DataFrame:
        """A table containing the value of each assignment for each student.

        The "value" of an assignment is the amount that it contributes to the student's
        overall score in the class. In short, it is the product of that assignment's
        score with its overall weight. The total of a student's assignment values equals
        their score in the class, with one caveat: if extra credit is allowed and a
        group's score is capped at 100%, the sum of the values in that group may exceed
        a student's actual score.

        This produces a table of the same size as :attr:`points_earned` where each entry
        contains the value of an assignment for a given student.

        If :attr:`grading_groups` is not set, all entries are `NaN`.


        This is a derived attribute; it should not be modified.

        Raises
        ------
        ValueError
            If all assignments in a group have been dropped for a student,
            the weights are undefined.

        """
        return (self.points_earned / self.points_possible) * self.overall_weight

    # properties: scores ---------------------------------------------------------------

    @property
    def grading_group_scores(self) -> pd.DataFrame:
        """A table of the scores earned in each grading group.

        Produces a DataFrame with a row for each student and a column for each
        grading group in which each entry is the student's score within that
        grading group.

        This takes into account dropped assignments and extra credit. Extra credit
        assignments do not count towards the total points possible in the group, but do
        count towards the points earned and thus the score.

        If a grading group has the `cap_total_score_at_100_percent` attribute set to
        `True`, the total score for that group is capped at 100%.

        If an assignment has a score of `NaN`, it is treated as a zero for the
        purposes of computing the grading group score. Conceptually, an
        individual assignment may not be attempted by a student, but a grading
        group score is always "attempted" and so it cannot be `NaN`.

        If :attr:`grading_groups` has not yet been set, all entries are `NaN`.

        This is a derived attribute; it should not be modified.

        """
        group_values = pd.DataFrame(
            {
                group_name: self.value[list(group.assignment_weights)].sum(axis=1)
                for group_name, group in self.grading_groups.items()
            }
        )
        group_weight = pd.Series(
            {
                group_name: _coerce_extra_credit_to_float(group.group_weight)
                for group_name, group in self.grading_groups.items()
            }
        )

        group_scores = group_values / group_weight

        # cap the total score at 100% if requested
        for group_name, group in self.grading_groups.items():
            if group.cap_total_score_at_100_percent:
                group_scores[group_name] = group_scores[group_name].clip(upper=1)

        return group_scores

    def _by_grading_group_to_by_assignment(self, by_group) -> pd.DataFrame:
        """Creates a students-by-assignments table from a students-by-groups table by tiling.

        Parameters
        ----------
        by_group
            Can be a Series or a DataFrame. If it is a DataFrame, it should
            have group names as columns and students in the index. Each
            column is "expanded" by creating a new column for each
            assignment in the group whose value is a copy of the group's
            column in the input. If a Series, it should have group names as
            its index. The Series is first converted to a students-by-groups
            dataframe by copying the group value for each student, then to a
            (student, assignments) dataframe using the above procedure.

        Returns
        -------
        DataFrame

        """

        def _convert_df(df):
            """Converts a students-by-groups dataframe to a students-by-assignments dataframe."""
            new_columns = {}
            for group_name in df.columns:
                for assignment in self.grading_groups[group_name].assignment_weights:
                    new_columns[assignment] = df[group_name]
            return pd.DataFrame(new_columns, index=pd.Index(self.students))

        def _convert_series(s):
            """Converts a Series with group names as its index to a students-by-assignments dataframe."""
            new_columns = {}
            for group_name in s.index:
                new_columns[group_name] = np.repeat(
                    s[group_name], len(self.points_earned)
                )
            df = pd.DataFrame(new_columns, index=pd.Index(self.students))
            return _convert_df(df)

        if isinstance(by_group, pd.Series):
            return _convert_series(by_group)
        else:
            return _convert_df(by_group)

    def _everyone_to_per_student(self, s: pd.Series) -> pd.DataFrame:
        """Converts a (groups,) or (assignments,) Series to a (students, *) DataFrame.

        That is, given a Series with group or assignment names as its index,
        creates a DataFrame with one row per student and one column per group
        or assignment, where each entry is the value of the Series for that
        group or assignment (each row is a copy of the Series).

        """
        return pd.DataFrame(
            np.tile(np.array(s.values), (len(self.points_earned), 1)),
            columns=s.index,
            index=pd.Index(self.students),
        )

    @property
    def attempted(self) -> pd.DataFrame:
        """A table of whether each assignment was attempted (i.e., turned in).

        Produces a DataFrame with a row for each student and a column for each
        assignment. Each entry is `True` if the student attempted the
        assignment and `False` otherwise. An assignment is considered
        "attempted" if `points_earned` is not `NaN`.

        """
        return ~self.points_earned.isna()

    @property
    def score(self) -> pd.DataFrame:
        """A table of scores on each assignment.

        Produces a DataFrame with a row for each student and a column for each assignment
        containing the number of points earned on that assignment as a proportion of
        the number of points possible on that assignment.

        If the student did not attempt the assignment (and so the `points_earned` entry
        is `NaN`), the score is also `NaN`.

        Does not take into account drops.

        This is a derived attribute; it should not be modified.

        """
        return self.points_earned / self.points_possible

    @property
    def overall_score(self) -> pd.Series:
        """A series containing the overall score earned by each student.

        A pandas Series with an entry for each student in the Gradebook. The
        index is the same as the series returned by the :attr:`students`
        attribute. Each entry is the overall score in the class, taking drops
        into account.

        This is a derived attribute; it should not be modified.

        Raises
        ------
        ValueError
            If :attr:`grading_groups` has not yet been set.

        """
        if not self.grading_groups:
            raise ValueError(
                "Grading groups should be set before calculating letter grades."
            )

        # we previously used the `value` attribute here by summing the values of all
        # assignments. However, this does not take into account the fact that grading
        # group scores can be capped at 100%. Instead, we compute the overall score by
        # multiplying the weights of each group by the group scores (which does take
        # into account the cap). This is equivalent to summing the values of all
        # assignments if there is no cap / extra credit.

        # we don't use the `value` attribute here because it does not take into account
        # grading groups that are capped at 100%.

        group_weight = pd.Series(
            {
                group_name: _coerce_extra_credit_to_float(group.group_weight)
                for group_name, group in self.grading_groups.items()
            }
        )

        # multiply the two together to get the overall score
        return (group_weight * self.grading_group_scores).sum(axis=1)

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

    def _replace(self, **kwargs) -> "Gradebook":
        """Create a new gradebook with some attributes replaced.

        By default, all attributes are copied. Any attributes that are
        provided as keyword arguments are replaced with the provided values.

        """
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

    def copy(self) -> "Gradebook":
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
        points_possible: Union[float, int],
        lateness: Optional[pd.Series] = None,
        dropped: Optional[pd.Series] = None,
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
            How late each student turned in the assignment. Turning in the assignment
            on time should be represented by a pd.Timedelta of zero seconds.
            Default: all zero seconds.
        dropped : Series[bool]
            Whether the assignment should be dropped for any given student.
            Default: all False.

        Raises
        ------
        ValueError
            If an assignment with the given name already exists, or if grades
            for a student are missing / grades for an unknown student are
            provided.

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
        self.points_possible[name] = float(points_possible)
        self.lateness[name] = lateness
        self.dropped[name] = dropped

    def restrict_to_assignments(self, assignments: Collection[str]):
        """Restrict the gradebook to only the supplied assignments, removing all others.

        Modifies the gradebook in-place.

        If the :attr:`grading_groups` attribute been set, it is reset to
        an empty dictionary by this operation.

        Parameters
        ----------
        assignments : Collection[str]
            A collection of assignment names.

        """
        assignments = list(assignments)
        extras = set(assignments) - set(self.assignments)
        if extras:
            raise KeyError(f"These assignments were not in the gradebook: {extras}.")

        self.points_earned = self.points_earned.loc[:, assignments]
        self.points_possible = self.points_possible.loc[assignments]
        self.lateness = self.lateness.loc[:, assignments]
        self.dropped = ensure_df(self.dropped.loc[:, assignments])

        self.grading_groups = {}

    def remove_assignments(self, assignments: Collection[str]):
        """Removes assignments from the gradebook.

        Modifies the gradebook in-place.

        If the :attr:`grading_groups` attribute been set, it is reset to
        an empty dictionary by this operation.

        Parameters
        ----------
        assignments : Collection[str]
            A collection of assignments names that will be removed.

        """
        assignments = list(assignments)
        extras = set(assignments) - set(self.assignments)
        if extras:
            raise KeyError(f"These assignments were not in the gradebook: {extras}.")

        return self.restrict_to_assignments(
            list(set(self.assignments) - set(assignments))
        )

    def rename_assignments(self, mapping: Mapping[str, str]):
        """Renames assignments.

        Modifies the gradebook in-place.

        If the :attr:`grading_groups` attribute been set, it is reset to
        an empty dictionary by this operation.

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

    def restrict_to_students(self, to: Collection[Union[str, Student]]):
        """Restrict the gradebook to only the supplied PIDs.

        Parameters
        ----------
        to : Collection[Union[str, Student]]
            A collection of PIDs or Students.

        Raises
        ------
        KeyError
            If a PID was specified that is not in the gradebook.

        """
        pids = [s.pid if isinstance(s, Student) else s for s in to]
        extras = set(pids) - set(self.pids)
        if extras:
            raise KeyError(f"These students were not in the gradebook: {extras}.")

        self.points_earned = self.points_earned.loc[pids]
        self.lateness = self.lateness.loc[pids]
        self.dropped = self.dropped.loc[pids]

    # notes ----------------------------------------------------------------------------

    def add_note(self, student: Student, channel: str, message: str):
        """Add a grading note.

        Mutates the gradebook.

        Parameters
        ----------
        student : Student
            The student for which the note should be added.

        channel : str
            The channel that the note should be added to. Valid channels are:
                - lates
                - drops
                - attempts
                - misc

        message : str
            The note's message.

        """
        if channel not in {"lates", "drops", "attempts", "misc"}:
            raise ValueError(f'Unknown channel "{channel}".')

        if student not in self.notes:
            self.notes[student] = {}

        if channel not in self.notes[student]:
            self.notes[student][channel] = []

        self.notes[student][channel].append(message)
