"""Core data types for managing grades."""

import collections.abc
import copy
import dataclasses

from .scales import DEFAULT_SCALE

import pandas as pd


# Student
# ======================================================================================


class Student:
    """Represents a student.

    Contains both a `pid` (identification string) and (optionally) a `name`
    attribute. The repr is such that the name is printed if available,
    otherwise the pid is printed. However, equality checks always use the pid.

    Used in the indices of tables in the Gradebook class. This allows code like:

    .. code::

        gradebook.points_marked.loc['A1000234', 'homework 03']

    which looks up the the number points marked for Homework 01 by student 'A1000234'.
    But when the table is printed, the student's name will appear instead of their pid.

    """

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


# Assignments
# ======================================================================================


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
        :meth:`Gradebook.combine_assignments`

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


# Deductions
# ======================================================================================


class _GradeAmount:

    def __init__(self, amount):
        self.amount = amount

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.amount == other.amount


class Points(_GradeAmount):
    pass


class Percentage(_GradeAmount):
    pass

# Gradebook
# ======================================================================================


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


@dataclasses.dataclass
class GradebookOptions:

    # number of seconds within which a late assignment is not considered late
    lateness_fudge: int = 5 * 60


@dataclasses.dataclass
class Group:
    name: str
    assignments: Assignments
    normalize_weights: bool = False


class Gradebook:
    """Data structure which facilitates common grading operations.

    Parameters
    ----------
    points_marked : pandas.DataFrame
        A dataframe with one row per student, and one column for each assignment.
        Each entry should be the raw number of points earned by the student on the
        given assignment without any deductions, e.g., for lateness. The index
        of the dataframe should consist of Student objects.
    points_possible : pandas.Series
        A series containing the maximum number of points possible for each
        assignment. The index of the series should match the columns of the
        `points_marked` dataframe.
    lateness : Optional[pandas.DataFrame]
        A dataframe of pd.Timedelta objects with the same columns/index as
        `points_marked`. An entry in the dataframe tells how late a student
        turned in the assignment. If `None` is passed, a dataframe of zero
        second timedeltas is used by default.
    dropped : Optional[pandas.DataFrame]
        A Boolean dataframe with the same columns/index as `points_marked`. An
        entry that is `True` indicates that the assignment should be dropped.
        If `None` is passed, a dataframe of all `False`s is used by default.
    deductions : Optional[dict]
        A nested dictionary of deductions. The keys of the outer dictionary
        should be student PIDs, and the values should be dictionaries. The keys
        of these inner dictionaries should be assignment names, and the values
        should be iterables of either Points or Percentage objects. If `None`
        is passed, an empty dictionary is used by default.
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
        "points_marked",
        "points_possible",
        "lateness",
        "dropped",
        "deductions",
        "notes",
        "opts",
    ]

    def __init__(
        self,
        points_marked,
        points_possible,
        lateness=None,
        dropped=None,
        deductions=None,
        notes=None,
        opts=None,
    ):
        self.points_marked = _cast_index(points_marked)
        self.points_possible = _cast_index(points_possible)
        self.lateness = (
            lateness if lateness is not None else _empty_lateness_like(points_marked)
        )
        self.dropped = (
            dropped if dropped is not None else _empty_mask_like(points_marked)
        )
        self.deductions = {} if deductions is None else deductions
        self.notes = {} if notes is None else notes
        self.opts = opts if opts is not None else GradebookOptions()

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} object with "
            f"{len(self.assignments)} assignments "
            f"and {len(self.pids)} students>"
        )

    # properties
    # ----------

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
    def students(self):
        """All students as Student objects.

        Returned in the order they appear in the indices of the `points_marked`
        attribute.

        Returns
        -------
        List[Student]

        """
        return [s for s in self.points_marked.index]

    @property
    def late(self):
        """A boolean dataframe telling which assignments were turned in late.

        Will have the same index and columns as the `points_marked` attribute.

        This is computed from the `.lateness` using the `.opts.lateness_fudge`
        option. If the lateness is less than the lateness fudge, the assignment
        is considered on-time; otherwise, it is considered late. This can be
        useful to work around grade sources whose reported lateness is not
        always reliable, such as Gradescope.

        """
        fudge = self.opts.lateness_fudge
        return self.lateness > pd.Timedelta(fudge, unit="s")

    @property
    def points_after_deductions(self):
        """A dataframe of points earned after taking deductions into account.

        Will have the same index and columns as the `points_marked` attribute.

        Deductions are applied in the order they appear in the `deductions` attribute.
        A percentage deduction is calculated *after* applying earlier deductions. For
        example, if 100 points are marked and two percentage deductions of 30% and 10%
        are applied, the result is 100 points * 70% * 90% = 63 points.

        This does not take drops into account.

        """
        points = self.points_marked.copy()

        def _apply_deduction(pid, assignment, deduction):
            p = points.loc[pid, assignment]

            if isinstance(deduction, Points):
                d = deduction.amount
            else:
                # calculate percentage deduction based on points possible
                d = deduction.amount * self.points_possible.loc[assignment]

            points.loc[pid, assignment] = max(p - d, 0)

        for pid, assignments_dct in self.deductions.items():
            for assignment, deductions in assignments_dct.items():
                for deduction in deductions:
                    _apply_deduction(pid, assignment, deduction)

        return points

    # copying / replacing
    # -------------------

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

    # misc

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
            return name_query in student.name.lower()

        [match] = [s for s in self.students if is_match(s)]
        return match


# MutableGradebook
# ======================================================================================


def _concatenate_deductions(gradebooks):
    """Concatenates the deductions from a sequence of gradebooks."""
    deductions = {}
    for gradebook in gradebooks:
        for pid, assignments_dct in gradebook.deductions.items():
            if pid not in deductions:
                deductions[pid] = {}

            for assignment in assignments_dct:
                deductions[pid][assignment] = assignments_dct[assignment]

    return deductions


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


def combine_gradebooks(gradebooks, restricted_to_pids=None):
    """Create a gradebook by safely combining several existing gradebooks.

    It is crucial that the combined gradebooks have exactly the same
    students -- we don't want students to have missing grades. This
    function checks to make sure that the gradebooks have the same students
    before combining them. Similarly, it verifies that each gradebook has
    unique assignments, so that no conflicts occur when combining them.

    The new gradebook's deductions are a union of the deductions in the
    existing gradebooks, as are the notes. The options are reset to their
    defaults.

    Parameters
    ----------
    gradebooks : Collection[Gradebook]
        The gradebooks to combine. Must have matching indices and unique
        column names.
    restricted_to_pids : Collection[str] or None
        If provided, each input gradebook will be restricted to the PIDs
        given before attempting to combine them. This is a convenience
        option, and it simply calls :meth:`Gradebook.restricted_to_pids` on
        each of the inputs.  Default: None

    Returns
    -------
    MutableGradebook
        A gradebook combining all of the input gradebooks.

    Raises
    ------
    ValueError
        If the PID indices of gradebooks do not match, or if there is a
        duplicate assignment name.

    """
    gradebooks = list(gradebooks)

    if restricted_to_pids is not None:
        gradebooks = [g.restricted_to_pids(restricted_to_pids) for g in gradebooks]

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
    maximums = concat_attr("points_possible", axis=0)
    lateness = concat_attr("lateness")
    dropped = concat_attr("dropped")

    deductions = _concatenate_deductions(gradebooks)
    notes = _concatenate_notes(gradebooks)

    return MutableGradebook(
        points, maximums, lateness, dropped, deductions=deductions, notes=notes
    )



def _combine_and_convert_deductions(parts, new_name, deductions, points_possible):
    """Concatenates all deductions from the given parts.

    Converts percentage deductions to points deductions along the way.

    Used in .combine_assignments

    """

    # combine and convert deductions
    def _convert_deduction(assignment, deduction):
        if isinstance(deduction, Percentage):
            possible = points_possible.loc[assignment]
            return Points(possible * deduction.amount)
        else:
            return deduction

    new_deductions = {}
    for student, assignments_dct in deductions.items():
        new_deductions[student] = {}

        combined_deductions = []
        for assignment, deductions_lst in assignments_dct.items():
            deductions_lst = [_convert_deduction(assignment, d) for d in deductions_lst]
            if assignment in parts:
                combined_deductions.extend(deductions_lst)
            else:
                new_deductions[student][assignment] = deductions_lst

        new_deductions[student][new_name] = combined_deductions

    return new_deductions


class MutableGradebook(Gradebook):
    """A gradebook with methods for changing assignments and grades."""

    # class methods
    # -------------

    # methods: adding/removing assignments/students
    # ---------------------------------------------

    def with_assignment(
        self, name, points_marked, points_possible, lateness=None, dropped=None
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
        points_marked : Series[float]
            A Series of points earned by each student.
        points_possible : float
            The maximum number of points possible on the assignment.
        lateness : Series[pd.Timedelta]
            How late each student turned in the assignment late. Default: all
            zero seconds.
        dropped : Series[bool]
            Whether the assignment should be dropped for any given student.
            Default: all False.

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
            lateness = pd.to_timedelta(pd.Series(0, index=self.students), unit="s")

        if dropped is None:
            dropped = pd.Series(False, index=self.students)

        result = self.copy()

        def _match_pids(pids, where):
            """Ensure that pids match."""
            theirs = set(pids)
            ours = set(self.pids)
            if theirs - ours:
                raise ValueError(f'Unknown pids {theirs - ours} provided in "{where}".')
            if ours - theirs:
                raise ValueError(f'"{where}" is missing PIDs: {ours - theirs}')

        _match_pids(points_marked.index, "points")
        _match_pids(lateness.index, "late")
        _match_pids(dropped.index, "dropped")

        result.points_marked[name] = points_marked
        result.points_possible[name] = points_possible
        result.lateness[name] = lateness
        result.dropped[name] = dropped

        return result

    def restricted_to_assignments(self, assignments):
        """Restrict the gradebook to only the supplied assignments.

        Any deductions that reference a removed assignment are also removed.

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
        r_maximums = self.points_possible[assignments].copy()
        r_lateness = self.lateness.loc[:, assignments].copy()
        r_dropped = self.dropped.loc[:, assignments].copy()

        # keep only the deductions which are for assignments in `assignments`
        r_deductions = copy.deepcopy(self.deductions)
        for student, assignments_dct in r_deductions.items():
            assignments_dct = {
                k: v for k, v in assignments_dct.items() if k in assignments
            }
            r_deductions[student] = assignments_dct

        return self._replace(
            points_marked=r_points,
            points_possible=r_maximums,
            lateness=r_lateness,
            dropped=r_dropped,
            deductions=r_deductions,
        )

    def without_assignments(self, assignments):
        """Returns a new gradebook instance without the given assignments.

        Any deductions that reference a removed assignment are also removed.

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

        return self.restricted_to_assignments(set(self.assignments) - set(assignments))

    def _combine_assignment(self, new_name, parts):
        """A helper function to combine assignments under the new name."""
        parts = list(parts)
        if self.dropped[parts].any(axis=None):
            raise ValueError("Cannot combine assignments with drops.")

        assignment_points = self.points_marked[parts].sum(axis=1)
        assignment_max = self.points_possible[parts].sum()
        assignment_lateness = self.lateness[parts].max(axis=1)

        new_points = self.points_marked.copy().drop(columns=parts)
        new_max = self.points_possible.copy().drop(parts)
        new_lateness = self.lateness.copy().drop(columns=parts)

        new_points[new_name] = assignment_points
        new_max[new_name] = assignment_max
        new_lateness[new_name] = assignment_lateness

        # combines deductions from all of the parts, converting Percentage
        # to Points along the way.
        new_deductions = _combine_and_convert_deductions(
            parts, new_name, self.deductions, self.points_possible
        )

        # we're assuming that dropped was not set; we need to provide an empy
        # mask here, else ._replace will use the existing larger dropped table
        # of self, which contains all parts
        new_dropped = _empty_mask_like(new_points)

        return self._replace(
            points_marked=new_points,
            points_possible=new_max,
            dropped=new_dropped,
            lateness=new_lateness,
            deductions=new_deductions,
        )

    def combine_assignments(self, dct_or_callable):
        """Combine the assignment parts into one single assignment with the new name.

        Sometimes assignments may have several parts which are recorded separately
        in the grading software. For instance, a homework might
        have a written part and a programming part. This method makes it easy
        to combine these parts into a single assignment.

        The individual assignment parts are removed from the gradebook.

        The new marked points and possible points are calculated by addition.
        The lateness of the new assignment is the *maximum* lateness of any of
        its parts.

        Deductions are concatenated. Points are propagated unchanged, but
        Percentage objects are converted to Points according to the ratio of
        the part's value to the total points possible. For example, if the
        first part is worth 70 points, and the second part is worth 30 points,
        and a 25% Percentage is applied to the second part, it is converted to
        a 25% * 30 = 7.5 point Points.

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
        `homework 02`, `homework 02 - programming`, etc., the following will "combine" the
        assignments into `homework 01`, `homework 02`, etc:

            >>> gradebook.combine_assignments(lambda s: s.split('-')[0].strip())

        Alternatively, you could write:

            >>> gradebook.combine_assignments({
                'homework 01': {'homework 01', 'homework 01 - programming'},
                'homework 02': {'homework 02', 'homework 02 - programming'}
                })

        """
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
            result = result._combine_assignment(key, value)
        return result

    def restricted_to_pids(self, to):
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

        return self._replace(
            points_marked=r_points, lateness=r_lateness, dropped=r_dropped
        )

    def add_note(self, pid, channel, message):
        """Convenience method for adding a note.

        Mutates the gradebook.

        Parameters
        ----------
        pid : str
            The pid of the student for which the note should be added.

        channel : str
            The channel that the note should be added to. Should be one of
            "drop", "late", or "misc".

        message : str
            The note's message.

        """
        valid_channels = {"drop", "late", "misc"}
        if channel not in valid_channels:
            raise ValueError(
                f"Channel {channel} unrecognized. Must be one of {valid_channels}."
            )

        if pid not in self.notes:
            self.notes[pid] = {}

        if channel not in self.notes[pid]:
            self.notes[pid][channel] = []

        self.notes[pid][channel].append(message)

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
        MutableGradebook
            The result of the last transformation in the sequence.

        """
        try:
            transformations = list(transformations)
        except TypeError:
            transformations = [transformations]

        result = self
        for transformation in transformations:
            result = transformation(result)

        return result

    def finalize(self, groups=None, scale=None):
        """Return a FinalizedGradebook from this MutableGradebook."""
        return FinalizedGradebook(
            points_marked=self.points_marked,
            points_possible=self.points_possible,
            lateness=self.lateness,
            dropped=self.dropped,
            deductions=self.deductions,
            notes=self.notes,
            opts=self.opts,
            groups=groups,
            scale=scale,
        )

    def grade(self, steps, groups=None, scale=None):
        self.apply(steps).finalize(groups, scale)

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
        # TODO: probably will remove this, move functionality to FinalizedGradebook when
        # we compute group scores
        extra = set(within) - set(self.assignments)
        if extra:
            raise ValueError(f"These assignments are not in the gradebook: {extra}.")

        within = list(within)

        scores = self.points_marked[within] / self.points_possible[within]

        new_points_possible = self.points_possible.copy()
        new_points_possible[within] = 1
        new_points_marked = self.points_marked.copy()
        new_points_marked.loc[:, within] = scores

        return self._replace(
            points_marked=new_points_marked, points_possible=new_points_possible
        )


# FinalizedGradebook
# ======================================================================================


class FinalizedGradebook(Gradebook):

    # methods: summaries and scoring
    # ------------------------------

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
        points_with_lates_as_zeros = points_with_lates_as_zeros[within]

        # create a full array of points available
        points_possible = self.points_marked.copy()[within]
        points_possible.iloc[:, :] = self.points_possible[within].values

        effective_points = points_with_lates_as_zeros[~self.dropped].sum(axis=1)
        effective_possible = points_possible[~self.dropped].sum(axis=1)

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
