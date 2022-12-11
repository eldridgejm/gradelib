"""A class representing a student."""

import typing


class Student:
    """Represents a student.

    Contains both a `pid` (identification string) and (optionally) a `name`
    attribute. The repr is such that the name is printed if available,
    otherwise the pid is printed. However, equality checks always use the pid.

    Used in the indices of tables in the Gradebook class. This allows code like:

    .. code::

        gradebook.points_earned.loc['A1000234', 'homework 03']

    which looks up the the number points marked for Homework 01 by student 'A1000234'.
    But when the table is printed, the student's name will appear instead of their pid.

    If the name is not available, the `name` attribute will be `None`.

    """

    def __init__(self, pid, name=None):
        self.pid = pid
        self.name = name

    def __repr__(self):
        """String representation uses name, if available; PID otherwise."""
        if self.name is not None:
            s = self.name
        else:
            s = self.pid

        return f"<{s}>"

    def __hash__(self):
        return hash(self.pid)

    def __eq__(self, other):
        """Equality checks always use the pid."""
        if isinstance(other, Student):
            return other.pid == self.pid
        else:
            return self.pid == other


class Students(typing.Sequence[Student]):
    """A sequence of students. Behaves like a list of :class:`Student` instances."""

    def __init__(self, students: typing.Sequence[Student]):
        self._students = students

    def __getitem__(self, ix):
        return self._students[ix]

    def __len__(self):
        return len(self._students)

    def find(self, name_query: str):
        """Finds a student from a fragment of their name.

        The search is case-insensitive.

        Parameters
        ----------
        name_query : str
            A string used to search for a student.

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

        matches = [s for s in self._students if is_match(s)]

        if len(matches) == 0:
            raise ValueError(f"No names matched {name_query}.")

        if len(matches) > 1:
            raise ValueError(f'Too many names matched "{name_query}": {matches}')

        return matches[0]
