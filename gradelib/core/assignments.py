import collections


# Assignments
# ======================================================================================


class Normalized:
    def __init__(self, assignments):
        self.assignments = assignments


class Assignments(collections.abc.Sequence):
    """A sequence of assignments.

    Behaves essentially like a standard Python list, but has some additional
    methods which make it faster to create groups of assignments. In particular,
    :meth:`starting_with` and :meth:`containing`.
    """

    def __init__(self, names):
        self._names = list(names)

    # dunder methods -------------------------------------------------------------------

    def __contains__(self, element):
        return element in self._names

    def __len__(self):
        return len(self._names)

    def __iter__(self):
        return iter(self._names)

    def __eq__(self, other):
        return list(self) == list(other)

    def __add__(self, other):
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

    # helper methods -------------------------------------------------------------------

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


