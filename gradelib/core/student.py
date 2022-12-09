# Student
# ======================================================================================


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


