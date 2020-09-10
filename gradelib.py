"""A package for computing overall grades in courses @ UCSD."""

import collections.abc

import pandas


class AssignmentGroup(collections.abc.Collection):
    """A collection of assignments."""

    def __init__(self, names):
        self._names = set(names)

    def __contains__(self, element):
        return element in self._names

    def __len__(self):
        return len(self._names)

    def __iter__(self):
        return iter(self._names)

    def starting_with(self, prefix):
        return self.__class__(x for x in self._names if x.startswith(prefix))

    def containing(self, pattern):
        return self.__class__(x for x in self._names if pattern in x)

    def __repr__(self):
        return f'AssignmentGroup(names={self._names})'

    def __add__(self, other):
        return AssignmentGroup(self._names.union(other._names))


class Gradebook:
    """A collection of grades."""

    def __init__(self, points, maximums, late=None, dropped=None):
        self.points = points
        self.maximums = maximums
        self.late = late if late is not None else ...
        self.dropped = dropped if dropped is not None else ...

    @property
    def assignments(self):
        return AssignmentGroup(self.points.columns)
