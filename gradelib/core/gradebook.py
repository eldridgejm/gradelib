"""Core data types for managing grades."""

import collections.abc
import copy
import dataclasses
import typing

from ..scales import DEFAULT_SCALE, map_scores_to_letter_grades, average_gpa
from .. import plot as _plot
from .student import Student
from .assignments import Assignments, Normalized

import altair
import numpy as np
import pandas as pd


NORMALIZE = object()


# GradeAmounts
# ======================================================================================


class _GradeAmount:
    def __init__(self, amount):
        self.amount = amount

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.amount == other.amount

    def __repr__(self):
        return f"{self.__class__.__name__}(amount={self.amount!r})"


class Points(_GradeAmount):
    def __str__(self):
        return f"{self.amount} points"


class Percentage(_GradeAmount):
    def __str__(self):
        return f"{self.amount}%"


# Gradebook
# ======================================================================================

# helpers ------------------------------------------------------------------------------


def _normalize_selector(selector, assignments):
    if not callable(selector):
        if not isinstance(selector, dict):
            dct = {}
            for prefix in selector:
                dct[prefix] = {a for a in assignments if a.startswith(prefix)}
        else:
            dct = selector
    else:
        to_key = selector
        dct = {}
        for assignment in assignments:
            key = to_key(assignment)
            if key not in dct:
                dct[key] = []
            dct[key].append(assignment)

    return dct


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
    groups = []
    seen_group_names = set()
    for gradebook in gradebooks:
        groups.extend(gradebook.groups)
        current_group_names = set(g.name for g in gradebook.groups)
        names_seen_twice = seen_group_names & current_group_names
        if names_seen_twice:
            raise ValueError(f"Duplicate group names seen: {names_seen_twice}.")
        seen_group_names.update(current_group_names)

    return groups


def _combine_if_equal(gradebooks, attr):
    obj = None
    for gradebook in gradebooks:
        if obj is None:
            obj = getattr(gradebook, attr)
        else:
            if getattr(gradebook, attr) != obj:
                raise ValueError("Options do not match in all gradebooks.")

    return obj


def combine_gradebooks(gradebooks, restrict_to_pids=None):
    """Create a gradebook by safely combining several existing gradebooks.

    It is crucial that the combined gradebooks have exactly the same
    students -- we don't want students to have missing grades. This
    function checks to make sure that the gradebooks have the same students
    before combining them. Similarly, it verifies that each gradebook has
    unique assignments and group names, so that no conflicts occur when
    combining them.

    The new gradebook's groups are a union of the groups, as are the notes.

    If the scales are the same, the new scale is set to be the same as the old.
    If they are different, a ValueError is raised.

    If the options are the same, the new options are set to be the same as the
    old. If they are different, a ValueError is raised.

    Parameters
    ----------
    gradebooks : Collection[Gradebook]
        The gradebooks to combine. Must have matching indices and unique
        column names.
    restrict_to_pids : Collection[str] or None
        If provided, each input gradebook will be restrict to the PIDs
        given before attempting to combine them. This is a convenience
        option, and it simply calls :meth:`Gradebook.restrict_to_pids` on
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

    if restrict_to_pids is not None:
        for gradebook in gradebooks:
            gradebook.restrict_to_pids(restrict_to_pids)

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
        groups=_concatenate_groups(gradebooks),
        opts=_combine_if_equal(gradebooks, "opts"),
        scale=_combine_if_equal(gradebooks, "scale"),
    )


@dataclasses.dataclass
class GradebookOptions:

    # number of seconds within which a late assignment is not considered late
    lateness_fudge: int = 5 * 60


class Group:

    _attrs = [
        "name",
        "assignments",
        "weight",
    ]

    def __init__(
        self,
        name,
        assignments,
        weight,
    ):

        self.name = name
        if isinstance(assignments, Normalized):
            value = 1 / len(assignments.assignments)
            self.assignments = {a: value for a in assignments.assignments}
        else:
            self.assignments = assignments
        self.weight = weight

    def __eq__(self, other):
        return all(getattr(self, attr) == getattr(other, attr) for attr in self._attrs)


class Gradebook:
    """Data structure which facilitates common grading operations.

    Parameters
    ----------
    points_earned : pandas.DataFrame
        A dataframe with one row per student, and one column for each assignment.
        Each entry should be the raw number of points earned by the student on the
        given assignment. The index of the dataframe should consist of Student
        objects.
    points_possible : pandas.Series
        A series containing the maximum number of points possible for each
        assignment. The index of the series should match the columns of the
        `points_earned` dataframe.
    lateness : Optional[pandas.DataFrame]
        A dataframe of pd.Timedelta objects with the same columns/index as
        `points_earned`. An entry in the dataframe tells how late a student
        turned in the assignment. If `None` is passed, a dataframe of zero
        second timedeltas is used by default.
    dropped : Optional[pandas.DataFrame]
        A Boolean dataframe with the same columns/index as `points_earned`. An
        entry that is `True` indicates that the assignment should be dropped.
        If `None` is passed, a dataframe of all `False`s is used by default.
    notes : Optional[dict]
        A nested dictionary of notes, possibly used by report generating code.
        The keys of the outer dictionary should be student PIDs, and the values
        should be dictionaries. The keys of the inner dictionary should specify
        a note "channel", and can be either "late", "drop", or "misc"; these
        are signals to reporting code that help determine where to display
        notes. The values of the inner dictionary should be iterables of
        strings, each one a message.

    Notes
    -----
    Typically a Gradebook is not created manually, but is instead produced
    by reading grades exported from Gradescope or Canvas, using
    :func:`gradelib.io.gradescope.read` or :func:`gradelib.io.canvas.read`.

    """

    _kwarg_names = [
        "points_earned",
        "points_possible",
        "lateness",
        "dropped",
        "notes",
        "groups",
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
        groups=None,
        scale=None,
        opts=None,
    ):
        self.points_earned = _cast_index(points_earned)
        self.points_possible = points_possible
        self.lateness = (
            lateness if lateness is not None else _empty_lateness_like(points_earned)
        )
        self.dropped = (
            dropped if dropped is not None else _empty_mask_like(points_earned)
        )
        self.notes = {} if notes is None else notes
        self.groups = self.default_groups if groups is None else groups
        self.scale = DEFAULT_SCALE if scale is None else scale
        self.opts = opts if opts is not None else GradebookOptions()

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} object with "
            f"{len(self.assignments)} assignments "
            f"and {len(self.pids)} students>"
        )

    # properties -----------------------------------------------------------------------

    @property
    def assignments(self):
        """All assignments in the gradebook.

        Returns
        -------
        Assignments

        """
        return Assignments(self.points_earned.columns)

    @property
    def pids(self):
        """All student PIDs.

        Returns
        -------
        set

        """
        return set(self.points_earned.index)

    @property
    def students(self):
        """All students as Student objects.

        Returned in the order they appear in the indices of the `points_earned`
        attribute.

        Returns
        -------
        List[Student]

        """
        return [s for s in self.points_earned.index]

    @property
    def late(self):
        """A boolean dataframe telling which assignments were turned in late.

        Will have the same index and columns as the `points_earned` attribute.

        This is computed from the `.lateness` using the `.opts.lateness_fudge`
        option. If the lateness is less than the lateness fudge, the assignment
        is considered on-time; otherwise, it is considered late. This can be
        useful to work around grade sources whose reported lateness is not
        always reliable, such as Gradescope.

        """
        fudge = self.opts.lateness_fudge
        return self.lateness > pd.Timedelta(fudge, unit="s")

    # properties: groups ---------------------------------------------------------------

    @property
    def default_groups(self):
        weight = 1 / len(self.assignments)
        return tuple(
            Group(assignment, Assignments([assignment]), weight)
            for assignment in self.assignments
        )

    @property
    def groups(self):
        return tuple(self._groups)

    @groups.setter
    def groups(self, value):
        def _make_group(g):
            if isinstance(g, Group):
                args = [
                    g.name,
                    g.assignments,
                    g.weight,
                ]
            elif len(g) == 2:
                # expecting a single assignment
                args = (g[0], Assignments([g[0]]), g[1])
            elif len(g) == 3:
                args = list(g)
            else:
                raise TypeError("Unexpected type for groups.")

            if callable(args[1]):
                args[1] = args[1](self.assignments)

            return Group(*args)

        self._groups = [_make_group(g) for g in value]

    # properties: weights and values ---------------------------------------------------

    @property
    def weight(self):
        result = self.points_possible / self._by_group_to_by_assignment(
            self.group_points_possible_after_drops
        )

        for group in self.groups:
            if isinstance(group.assignments, dict):
                weights = pd.Series(group.assignments)
                weights = self._everyone_to_per_student(weights)
                weights = weights * ~self.dropped[list(group.assignments)]
                weights = (weights.T / weights.sum(axis=1)).T
                result.loc[:, list(group.assignments)] = weights

        return result * (~self.dropped)

    @property
    def overall_weight(self):
        group_weights = pd.Series({group.name: group.weight for group in self.groups})
        return self.weight * self._by_group_to_by_assignment(group_weights)

    @property
    def value(self):
        return (self.points_earned / self.points_possible) * self.overall_weight

    # properties: scores ---------------------------------------------------------------

    @property
    def group_points_possible_after_drops(self):
        result = {}
        for group in self.groups:
            possible = pd.DataFrame(
                np.tile(
                    self.points_possible[list(group.assignments)],
                    (self.points_earned.shape[0], 1),
                ),
                index=self.students,
                columns=list(group.assignments),
            )

            possible[self.dropped[list(group.assignments)]] = 0
            possible = possible.sum(axis=1)

            if (possible == 0).any():
                problematic_pids = list(possible.index[possible == 0])
                raise ValueError(
                    f"All assignments are dropped for {problematic_pids} in group '{group.name}'."
                )

            result[group.name] = possible

        return pd.DataFrame(result, index=self.students)

    @property
    def group_scores(self):
        group_values = pd.DataFrame(
            {
                group.name: self.value[list(group.assignments)].sum(axis=1)
                for group in self.groups
            }
        )
        group_weights = pd.Series({group.name: group.weight for group in self.groups})
        return group_values / group_weights

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
            for group in self.groups:
                if group.name == name:
                    return group

        def _convert_df(df):
            new_columns = {}
            for group_name in df.columns:
                for assignment in _get_group_by_name(group_name).assignments:
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
    def score(self):
        return self.points / self.points_possible

    @property
    def overall_score(self):
        return self.value.sum(axis=1)

    # properties: letter grades --------------------------------------------------------

    @property
    def letter_grades(self):
        return map_scores_to_letter_grades(self.overall_score, scale=self.scale)

    @property
    def letter_grade_distribution(self):
        counts = self.letter_grades.value_counts()
        distribution = {}
        for letter in self.scale:
            if letter in counts:
                distribution[letter] = counts.loc[letter]
            else:
                distribution[letter] = 0

        return pd.Series(distribution, name="Count")

    # properties: ranks and percentiles

    @property
    def rank(self):
        sorted_scores = self.overall_score.sort_values(ascending=False).to_frame()
        sorted_scores["rank"] = np.arange(1, len(sorted_scores) + 1)
        return sorted_scores["rank"]

    @property
    def percentile(self):
        s = 1 - ((self.rank - 1) / len(self.rank))
        s.name = "percentile"
        return s

    # summaries ------------------------------------------------------------------------

    def _assignment_plot(self, pid):
        data = self.score.loc[pid].to_frame(name="Score")
        data["Notes"] = self.dropped.loc[pid].apply(lambda d: "dropped" if d else "")

        data = (
            data.sort_index()
            .reset_index()
            .rename(columns={"index": "Assignment"})
            .reset_index()
            .fillna(0)
        )

        data["Formatted Score"] = data["Score"].apply(lambda s: f"{s * 100:0.2f}%")

        bars = (
            altair.Chart(data)
            .mark_bar()
            .encode(x="Score:Q", y="Assignment:N", tooltip="Formatted Score")
        )

        text = (
            altair.Chart(data)
            .mark_text(
                align="left",
                baseline="middle",
                color="black",
                fontWeight="bold",
                dx=3,  # Nudges text to right so it doesn't appear on top of the bar
            )
            .encode(x="Score:Q", y="Assignment:N", text="Notes:N")
        )

        return bars + text

    def _student_summary(self, student):
        from IPython.display import display, HTML

        lines = []

        def par(desc, msg):
            lines.append(f"<p><b>{desc}:</b> {msg}</p>")

        def li(desc, msg):
            lines.append(f"<li><b>{desc}:</b> {msg}</li>")

        def _fmt_as_pct(f):
            return f"{f * 100:0.2f}%"

        name = student.name
        pid = student.pid

        lines.append(f"<h1>Student Summary: {name} ({pid})</h1>")

        par("Overall score", f"{_fmt_as_pct(self.overall_score.loc[pid])}")
        par("Letter grade", self.letter_grades.loc[pid])
        par("Rank", f"{self.rank.loc[pid]} out of {len(self.rank)}")
        par("Percentile", f"{self.percentile.loc[pid]:0.2f}")

        lines.append("<h2>Group Scores</h2>")
        lines.append("<ul>")
        for group in self.groups:
            score = self.group_scores.loc[pid, group.name]
            li(group.name, _fmt_as_pct(score))
        lines.append("</ul>")

        notes = self.notes.get(pid, None)
        if notes is not None:
            lines.append("<h2>Notes</h2>")
            for channel in notes:
                lines.append(f"<h3>{channel.capitalize()}</h3>")
                lines.append("<ul>")
                for note in notes[channel]:
                    lines.append(f"<li>{note}</li>")
                lines.append("</ul>")

        display(HTML("\n".join(lines)))

        display(self._assignment_plot(pid))

    def _class_summary(self):
        from IPython.display import display, HTML

        lines = []

        def item(desc, msg):
            lines.append(f"<p><b>{desc}:</b> {msg}")

        lines.append("<h1>Class Summary</h1>")

        item("Number of students", len(self.students))

        lines.append("<h2>Letter Grades</h2>")

        lines.append(self.letter_grade_distribution.to_frame().T.to_html())

        agpa = average_gpa(self.letter_grades)
        lines.append(f"<p><b>Class GPA:</b> {agpa:0.2f}</p>")
        lines.append("<h2>Distribution</h2>")

        display(HTML("\n".join(lines)))

        display(_plot.grade_distribution(self))

    def summary(self, student=None):
        if student is not None:
            return self._student_summary(self.find_student(student))
        else:
            return self._class_summary()

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
        return self._replace()

    # find student ---------------------------------------------------------------------

    def find_student(self, name_query):
        """Finds a student from a fragment of their name.

        The search is case-insensitive.

        Returns
        -------
        Student
            The matching student.

        Raises
        ------
        ValueError
            If no student matches, or if more than one student matches.

        """

        def is_match(student):
            if student.name is None:
                return False
            return name_query.lower() in student.name.lower()

        matches = [s for s in self.students if is_match(s)]

        if len(matches) == 0:
            raise ValueError(f"No names matched {name_query}.")

        if len(matches) > 1:
            raise ValueError(f'Too many names matched "{name_query}": {matches}')

        return matches[0]

    # adding/removing assignments/students ---------------------------------------------

    def add_assignment(
        self, name, points_earned, points_possible, lateness=None, dropped=None
    ):
        """Adds a single assignment to the gradebook.

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

    def restrict_to_assignments(self, assignments):
        """Restrict the gradebook to only the supplied assignments.

        Groups are updated so that they reference only the assignments listed
        in `assignments`.

        Parameters
        ----------
        assignments : Collection[str]
            A collection of assignment names.

        Raises
        ------
        KeyError
            If an assignment was specified that was not in the gradebook.

        """
        assignments = list(assignments)
        extras = set(assignments) - set(self.assignments)
        if extras:
            raise KeyError(f"These assignments were not in the gradebook: {extras}.")

        self.points_earned = self.points_earned.loc[:, assignments]
        self.points_possible = self.points_possible[assignments]
        self.lateness = self.lateness.loc[:, assignments]
        self.dropped = self.dropped.loc[:, assignments]

        def _update_groups():
            def _update_group(g):
                kept_assignments = [a for a in g.assignments if a in assignments]
                return Group(g.name, kept_assignments, g.weight)

            new_groups_with_empties = [_update_group(g) for g in self.groups]
            return [g for g in new_groups_with_empties if g.assignments]

        self.groups = _update_groups()

    def remove_assignments(self, assignments):
        """Returns a new gradebook instance without the given assignments.

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
        # TODO preserve order better
        assignments = list(assignments)
        extras = set(assignments) - set(self.assignments)
        if extras:
            raise KeyError(f"These assignments were not in the gradebook: {extras}.")

        return self.restrict_to_assignments(set(self.assignments) - set(assignments))

    def restrict_to_pids(self, to):
        """Restrict the gradebook to only the supplied PIDS.

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

    def _combine_assignment_parts(self, new_name, parts):
        """A helper function to combine assignments under the new name."""
        parts = list(parts)
        if self.dropped[parts].any(axis=None):
            raise ValueError("Cannot combine assignments with drops.")

        assignment_points = self.points_earned[parts].sum(axis=1)
        assignment_max = self.points_possible[parts].sum()
        assignment_lateness = self.lateness[parts].max(axis=1)

        self.points_earned[new_name] = assignment_points
        self.points_possible[new_name] = assignment_max
        self.lateness[new_name] = assignment_lateness

        # we're assuming that dropped was not set; we need to provide an empy
        # mask here, else ._replace will use the existing larger dropped table
        # of self, which contains all parts
        self.dropped = _empty_mask_like(self.points_earned)

        self.remove_assignments(set(parts) - {new_name})

    def combine_assignment_parts(self, selector):
        """Combine the assignment parts into one single assignment with the new name.

        Sometimes assignments may have several parts which are recorded separately
        in the grading software. For instance, a homework might
        have a written part and a programming part. This method makes it easy
        to combine these parts into a single assignment.

        The individual assignment parts are removed from the gradebook.

        The new marked points and possible points are calculated by addition.
        The lateness of the new assignment is the *maximum* lateness of any of
        its parts.

        Points are propagated unchanged, but Percentage objects are converted
        to Points according to the ratio of the part's value to the total
        points possible. For example, if the first part is worth 70 points, and
        the second part is worth 30 points, and a 25% Percentage is applied to
        the second part, it is converted to a 25% * 30 = 7.5 point Points.

        It is unclear what the result should be if any of the assignments to be
        unified has been dropped, but other parts have not. For this reason,
        this method will raise a `ValueError` if *any* of the parts have been
        dropped.

        Groups updated so that the parts no longer appear in any group, but new
        groups are not created.

        Parameters
        ----------
        selector : Mapping[str, Collection[str]]
            Either: 1) a mapping whose keys are new assignment names, and whose
            values are collections of assignments that should be unified under
            their common key; 2) a list of prefixes; each prefix defines a
            group that should be combined; or 3) a callable which maps
            assignment names to new assignment by which they should be grouped.

        Raises
        ------
        ValueError
            If any of the assignments to be unified is marked as dropped. See above for
            rationale.

        Example
        -------

        Assuming the gradebook has assignments named `homework 01`, `homework 01 - programming`,
        `homework 02`, `homework 02 - programming`, etc., the following will "combine" the
        assignments into `homework 01`, `homework 02`, etc:

            >>> gradebook.combine_assignment_parts(lambda s: s.split('-')[0].strip())

        Alternatively, you could write:

            >>> gradebook.combine_assignment_parts(["homework 01", "homework 02"])

        Or:

            >>> gradebook.combine_assignment_parts({
                'homework 01': {'homework 01', 'homework 01 - programming'},
                'homework 02': {'homework 02', 'homework 02 - programming'}
                })


        """
        dct = _normalize_selector(selector, self.assignments)

        for key, value in dct.items():
            self._combine_assignment_parts(key, value)

    def _combine_assignment_versions(self, new_name, versions):
        """A helper function to combine assignments under the new name."""
        versions = list(versions)
        if self.dropped[versions].any(axis=None):
            raise ValueError("Cannot combine assignments with drops.")

        # check that points are not earned in multiple versions
        assignments_turned_in = (~pd.isna(self.points_earned)).sum(axis=1)
        if (assignments_turned_in > 1).any():
            students = assignments_turned_in[assignments_turned_in > 1].index
            msg = f"{list(students)} turned in more than one version."
            raise ValueError(msg)

        # check that there's no lateness in any version
        total_lateness = self.lateness[versions].sum(axis=1)
        if total_lateness.any():
            msg = "Cannot combine versions when some have been turned in late."
            raise ValueError(msg)

        assignment_points = self.points_earned[versions].max(axis=1)
        assignment_max = self.points_possible[versions[0]]
        assignment_lateness = self.lateness[versions].max(axis=1)

        self.points_earned[new_name] = assignment_points
        self.points_possible[new_name] = assignment_max
        self.lateness[new_name] = assignment_lateness

        # we're assuming that dropped was not set; we need to provide an empy
        # mask here, else ._replace will use the existing larger dropped table
        # of self, which contains all versions
        self.dropped = _empty_mask_like(self.points_earned)

        self.remove_assignments(set(versions) - {new_name})

    def combine_assignment_versions(self, selector):
        """Combine the assignment versions into one single assignment with the new name.

        Sometimes assignments may have several versions which are recorded separately
        in the grading software. For instance, multiple versions of a midterm may be
        distributed to prevent cheating.

        The individual assignment versions are removed from the gradebook and
        are unified into a single new version.

        It is assumed that all assignment versions have the same number of
        points possible. If this is not the case, a `ValueError` is raised.

        Similarly, it is assumed that no student earns points for more than one
        of the versions. If this is not true, a `ValueError` is raised.

        It is unclear what the result should be if any of the assignments to be
        unified has been dropped or is late, but other parts have not. If
        either of these assumptions are violated, this method will raise a
        `ValueError`.

        Groups are updated so that the versions no longer appear in any group, but
        new groups are not created.

        Parameters
        ----------
        selector : Mapping[str, Collection[str]]
            Either: 1) a mapping whose keys are new assignment names, and whose
            values are collections of assignments that should be unified under
            their common key; 2) a list of prefixes; each prefix defines a
            group that should be combined; or 3) a callable which maps
            assignment names to new assignment by which they should be grouped.

        Raises
        ------
        ValueError
            If any of the assumptions are violated. See above.

        Example
        -------

        Assuming the gradebook has assignments named `midterm - version a`,
        `midterm - version b`, `midterm - version c`, etc., the following will
        "combine" the assignments into `midterm`:

            >>> gradebook.combine_assignment_versions(lambda s: s.split('-')[0].strip())

        Alternatively, you could write:

            >>> gradebook.combine_assignment_versions(["midterm"])

        Or:

            >>> gradebook.combine_assignment_versions({
                'midterm': {'midterm - version a', 'midterm - version b', 'midterm - 'version c'},
                })


        """
        dct = _normalize_selector(selector, self.assignments)

        for key, value in dct.items():
            self._combine_assignment_versions(key, value)

    def rename_assignments(self, mapping):
        resulting_names = (set(self.assignments) - mapping.keys()) | set(
            mapping.values()
        )
        if len(resulting_names) != len(self.assignments):
            raise ValueError("Name clashes in renamed assignments.")

        def _update_key(key):
            if key in mapping:
                return mapping[key]
            else:
                return key

        def _update_assignments_dct(assignments_dct):
            return {_update_key(k): v for k, v in assignments_dct.items()}

        self.points_earned.rename(columns=mapping, inplace=True)
        self.points_possible.rename(index=mapping, inplace=True)
        self.lateness.rename(columns=mapping, inplace=True)
        self.dropped.rename(columns=mapping, inplace=True)

    # notes ----------------------------------------------------------------------------

    def add_note(self, pid, channel, message):
        """Convenience method for adding a note.

        Mutates the gradebook.

        Parameters
        ----------
        pid : str
            The pid of the student for which the note should be added.

        channel : str
            The channel that the note should be added to.

        message : str
            The note's message.

        """
        if pid not in self.notes:
            self.notes[pid] = {}

        if channel not in self.notes[pid]:
            self.notes[pid][channel] = []

        self.notes[pid][channel].append(message)

    # apply ----------------------------------------------------------------------------

    def apply(self, transformations):
        """Apply transformation(s) to the gradebook.

        A transformation is a callable that takes in a gradebook object and
        returns a gradebook object. No assumption is made as to whether the
        transformation mutates the input or produces a copy (it could return
        the instance given as input, for example).

        If a sequence of transformations is provided, the output of a
        transformation is used as the input to the next transformation in the
        sequence.

        The gradebook is copied before handing to the first transformation, so
        self is guaranteed to be unmodified. This allows transformations which
        mutate for performance reasons while still guaranteeing that the overall
        application does not mutate this gradebook.

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