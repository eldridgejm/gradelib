"""Class representing a collection of assignments."""

import collections.abc
import typing

AssignmentSelector = typing.Union[
    typing.Callable[["Assignments"], "Assignments"], "Assignments", typing.Sequence[str]
]

AssignmentGrouper = typing.Union[
    typing.Mapping[str, typing.Collection[str]],
    typing.Collection[str],
    typing.Callable[[str], str],
]


def normalize(assignments: typing.Collection[str]) -> typing.Dict[str, float]:
    """Create an assignment weight dict. in which every assignment is weighed equally.

    Useful when creating assignment groups. For instance:

        >>> gradebook.assignment_groups = (
        ...     ('homework', normalize(gradebook.assignments.starting_with('home')), 0.5)
        ...     ('labs', normalize(gradebook.assignments.starting_with('lab')), 0.5)
        ... )

    Parameters
    ----------
    assignments: Collection[str]
        The assignments to normalize.

    Returns
    -------
    dict[str, float]
        An assignment weight dictionary in which each assignment is weighed equally.

    Example
    -------
    >>> normalize(['foo', 'bar', 'baz', 'quux'])
    {'foo': 0.25, 'bar': 0.25, 'baz': 0.25, 'quux': 0.25}


    """
    n = len(assignments)
    return {a: 1 / n for a in assignments}


class Assignments(collections.abc.Sequence[str]):
    """A sequence of assignments.

    Behaves essentially like a standard Python list of strings, but has some
    additional methods which make it faster to create groups of assignments.

    """

    def __init__(self, names: typing.Sequence[str]):
        self._names = list(names)

    def __contains__(self, element):
        return element in self._names

    def __len__(self):
        return len(self._names)

    def __iter__(self):
        return iter(self._names)

    def __eq__(self, other):
        return list(self) == list(other)

    def __add__(self, other):
        """Unions :class:`Assignments`."""
        return Assignments(self._names + other._names)

    def __getitem__(self, index):
        return self._names[index]

    def __repr__(self):
        return f"Assignments(names={self._names})"

    def _repr_pretty_(self, p, cycle):
        p.text("Assignments(names=[\n")
        for name in self._names:
            p.text(f"  {name!r}\n")
        p.text("])")

    def starting_with(self, prefix: str) -> "Assignments":
        """Return only those assignments starting with the prefix.

        Parameters
        ----------
        prefix: str
            The prefix to search for.

        Returns
        -------
        Assignments
            Only those assignments starting with the prefix.

        """
        return self.__class__(x for x in self._names if x.startswith(prefix))

    def containing(self, substring: str) -> "Assignments":
        """Return only those assignments containing the substring.

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

    def group_by(self, to_key: typing.Callable[[str], str]) -> dict[str, "Assignments"]:
        """Group the assignments according to a key function.

        Parameters
        ----------
        to_key : Callable[[str], str]
            A function which accepts an assignment name and returns a string
            that will be used as the assignment's key in the resulting
            dictionary.

        Returns
        -------
        dict[str, Assignments]
            A dictionary mapping keys to collections of assignments.

        Example
        -------
        Suppose that the gradebook has assignments

            >>> assignments = gradelib.Assignments([
            ... "homework 01", "homework 01 - programming", "homework 02",
            ... "homework 03", "homework 03 - programming", "lab 01", "lab 02"
            ... ])
            >>> assignments.group_by(lambda s: s.split('-')[0].strip())
            {'homework 01': Assignments(names=['homework 01', 'homework 01 - programming']),
             'homework 02': Assignments(names=['homework 02']),
             'homework 03': Assignments(names=['homework 03', 'homework 03 - programming']),
             'lab 01': Assignments(names=['lab 01']),
             'lab 02': Assignments(names=['lab 02'])}

        See Also
        --------
        :meth:`Gradebook.combine_assignment_parts`
        :meth:`Gradebook.combine_assignment_versions`

        """
        dct = {}
        for assignment in self:
            key = to_key(assignment)
            if key not in dct:
                dct[key] = []
            dct[key].append(assignment)

        return {key: Assignments(value) for key, value in dct.items()}


class LazyAssignments:
    """A group of assignments that is lazily evaluated.

    This can be useful when working with a gradebook whose assignments are
    changing; for example, one in which there are multiple midterm versions
    that will be combined into one midterm. This can be used to create one
    assignment selector that is evaluated with the most up-to-date set of
    assignments, and therefore works to select assignments both before and
    after preprocessing.

    Parameters
    ----------
    f : Optional[Callable[[Assignments], Assignments]]
        A "filter" function which, given assignments, selects and returns some
        of them. If `None`, when called the assignments are returned
        immediately.

    Attributes
    ----------
    f : Optional[Callable[[Assignments], Assignments]]
        The filter function, or `None`.

    Example
    -------
    >>> assignments = Assignments(['hw01', 'hw02', 'lab01'])
    >>> homeworks = LazyAssignments().starting_with('hw')
    >>> homeworks(assignments)
    Assignments(['hw01', 'hw02'])
    >>> # alternatively, give a function
    >>> labs = LazyAssignments(lambda asmts: asmts.starting_with('lab'))
    >>> labs(assignments)
    Assignments(['lab01'])

    """

    def __init__(self, f: typing.Callable[[Assignments], Assignments]=None):
        self.f = f

    def __call__(self, asmts: Assignments) -> Assignments:
        """Apply the filter, returning :class:`Assignments`.

        Parameters
        ----------
        asmts : Assignments
            The input to the filter.

        Returns
        -------
        Assignments
            The filtered assignments.

        """
        if self.f is None:
            return asmts
        else:
            return self.f(asmts)

    def __add__(self, other: "LazyAssignments") -> "LazyAssignments":
        """Produces a :class:`LazyAssignments` that lazily unions the operands.

        Example
        -------
        >>> homeworks = gradelib.LazyAssignments(lambda a: a.starting_with('hw'))
        >>> labs = gradelib.LazyAssignments(lambda a: a.starting_with('lab'))
        >>> assignments = gradelib.Assignments(['hw01', 'hw02', 'lab01', 'lab02', 'exam'])
        >>> (homeworks + labs)(assignments)
        Assignments(['hw01', 'hw02', 'lab01', 'lab02'])

        """

        def closure(asmts):
            return self(asmts) + other(asmts)

        return LazyAssignments(closure)

    def starting_with(self, prefix: str) -> "LazyAssignments":
        """A lazy version of :meth:`Assignments.starting_with`.

        Example
        -------
        >>> assignments = gradelib.Assignments( ["hw 01", "hw 02", "hw 03", "lab 01"])
        >>> homeworks = gradelib.LazyAssignments(lambda asmts: asmts.starting_with('home'))
        >>> homeworks(assignments)
        Assignments(["hw 01", "hw 02", "hw 03"])

        """

        def closure(asmts):
            return self(asmts).starting_with(prefix)

        return LazyAssignments(closure)

    def containing(self, substring: str) -> "LazyAssignments":
        """A lazy version of :meth:`Assignments.containing`."""

        def closure(asmts):
            return self(asmts).containing(substring)

        return LazyAssignments(closure)

    def group_by(self, to_key: typing.Callable[[str], str]):
        """A lazy version of :meth:`Assignments.group_by`.

        Example
        -------
        >>> key = lambda s: s.split('-')[0]
        >>> hw_groups = LazyAssignments(lambda asmts: asmts.starting_with('hw')).group_by(key)
        >>> assignments = Assignments(['hw 01 - a', 'hw 01 - b', 'hw 02', 'lab 01'])
        >>> hw_groups(assignments)
        {'hw 01': {'hw 01 - a', 'hw 01 - b'}, 'hw 02'}

        """

        def closure(asmts):
            return self(asmts).group_by(to_key)

        return closure
