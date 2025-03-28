"""Represents a collection of assignments."""

from collections.abc import Sequence
import typing


class Assignments(Sequence[str]):
    """A sequence of assignments.

    Behaves essentially like a standard Python list of strings, but has some
    additional methods which make it faster to create groups of assignments.

    """

    def __init__(self, names: typing.Sequence[str]):
        self._names = list(names)

    def __contains__(self, element) -> bool:
        if not isinstance(element, str):
            return False
        return element in self._names

    def __len__(self) -> int:
        return len(self._names)

    def __iter__(self):
        return iter(self._names)

    def __eq__(self, other) -> bool:
        return list(self) == list(other)

    def __add__(self, other) -> "Assignments":
        """Concatenates two collections of :class:`Assignments`."""
        return Assignments(self._names + other._names)

    def __getitem__(self, index_or_slice) -> str:
        return self._names[index_or_slice]

    def __repr__(self) -> str:
        return f"Assignments(names={self._names})"

    def _repr_pretty_(self, p, _):
        """Pretty-printing for IPython."""
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
        return self.__class__([x for x in self._names if x.startswith(prefix)])

    def ending_with(self, suffix: str) -> "Assignments":
        """Return only those assignments ending with the suffix.

        Parameters
        ----------
        suffix: str
            The suffix to search for.

        Returns
        -------
        Assignments
            Only those assignments ending with the suffix.

        """
        return self.__class__([x for x in self._names if x.endswith(suffix)])

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
        return self.__class__([x for x in self._names if substring in x])

    def not_containing(self, substring: str) -> "Assignments":
        """Return only those assignments *not* containing the substring.

        Parameters
        ----------
        substring : str
            The substring to search for.

        Returns
        -------
        Assignments
            Only those assignments *not* containing the substring.

        """
        return self.__class__([x for x in self._names if substring not in x])

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

        .. testsetup::

            import gradelib

        .. doctest::
            :options: +NORMALIZE_WHITESPACE

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

    def group_by_splitting_on(self, separator: str) -> dict[str, "Assignments"]:
        """Group the assignments by splitting on a separator.

        This is a convenience method which is equivalent to calling
        :meth:`group_by` with a function that splits on the given separator,
        strips whitespace from the resulting strings, and returns the first
        part.

        Parameters
        ----------
        separator : str
            The separator to split on.

        Returns
        -------
        dict[str, Assignments]
            A dictionary mapping keys to collections of assignments.

        Example
        -------

        .. testsetup::

            import gradelib

        .. doctest::
            :options: +NORMALIZE_WHITESPACE

            >>> assignments = gradelib.Assignments([
            ... "homework 01", "homework 01 - programming", "homework 02",
            ... "homework 03", "homework 03 - programming", "lab 01", "lab 02"
            ... ])
            >>> assignments.group_by_splitting_on('-')
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
        return self.group_by(lambda s: s.split(separator)[0].strip())
