"""Representa a student in the class."""

import typing


class Student:
    """Represents a student.

    Attributes
    ----------
    pid : str
        The student's PID (identification string).
    name : Optional[str]
        The student's name. If not available, this will be `None`.

    When a :class:`Student` instance is printed, the student's name is displayed if
    available; however, when two :class:`Student` instances are compared for equality,
    the :code:`.pid` attribute is used.

    Used in the index of tables in the :class:`Gradebook` class. This allows
    code like:

    .. code::

        gradebook.points_earned.loc['A1000234', 'homework 03']

    which looks up the the number points marked for Homework 01 by student
    'A1000234'. But when the table is printed, the student's name will appear
    instead of their PID.

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

    def __lt__(self, other):
        """Less-than checks always use the pid."""
        if isinstance(other, Student):
            return self.pid < other.pid
        else:
            return self.pid < other


class Students(typing.Sequence[Student]):
    """A sequence of :class:`Student` instances.

    This behaves like a list of :class:`Student` instances, but also provides a
    :meth:`find` method that allows you to look up a student by (part of) their
    name.

    """

    def __init__(self, students: typing.Sequence[Student]):
        self._students = students

    def __getitem__(self, ix):
        return self._students[ix]

    def __len__(self):
        return len(self._students)

    def find(self, pattern: str) -> Student:
        """Finds a student from a substring of their name.

        The search is case-insensitive.

        Parameters
        ----------
        pattern : str
            A pattern to search for in the student's name. All students whose
            (lowercased) names contain this pattern as a substring will be
            considered matches.

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
            return pattern.lower() in student.name.lower()

        matches = [s for s in self._students if is_match(s)]

        if len(matches) == 0:
            raise ValueError(f"No names matched {pattern}.")

        if len(matches) > 1:
            raise ValueError(f'More than one name matched "{pattern}": {matches}')

        return matches[0]
