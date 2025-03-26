from collections.abc import Sequence
from typing import Union, Optional

import pandas as _pd


from ..core import Percentage, Points, Gradebook, Student

# private helpers ======================================================================


def _add_reason_to_message(message, reason):
    if reason is not None:
        message += " Reason: " + reason
    return message


def _convert_amount_to_absolute_points(amount, gradebook, assignment):
    if isinstance(amount, Points):
        return amount.amount
    else:
        # calculate percentage adjustment based on points possible
        return (amount.amount / 100) * gradebook.points_possible.loc[assignment]


# public functions and classes =========================================================

# make_exceptions ----------------------------------------------------------------------


def make_exceptions(
    gradebook: Gradebook,
    student: Union[Student, str],
    exceptions: Sequence[Union["ForgiveLate", "Drop", "Replace"]],
):
    """Make policy exceptions for individual students.

    Parameters
    ----------
    gradebook : Gradebook
        The gradebook to apply the exceptions to. Will be modified.

    student: Union[Student, str]
        The student to apply the exceptions to. Can be a :class:`Student` object
        or a string that will be used to find the student.

    exceptions : Sequence[Union[ForgiveLate, Drop, Replace]]
        A sequence of exceptions to apply to the student. Each exception should
        be an instance of :class:`ForgiveLate`, :class:`Drop`, or :class:`Replace`.

    Example
    -------

    .. testsetup::

        import pandas as pd
        import gradelib

        columns = ["hw01", "hw02", "hw03", "lab01"]
        students = [gradelib.Student("A1", "Justin"), gradelib.Student("A2", "Steve")]
        p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
        p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
        points_earned = pd.DataFrame([p1, p2], index=gradelib.Students(students))
        points_possible = pd.Series([2, 50, 100, 20], index=columns)
        gradebook = gradelib.Gradebook(points_earned, points_possible)

    .. testcode::

        from gradelib.policies.exceptions import make_exceptions, ForgiveLate, Drop
        make_exceptions(gradebook, "Justin", [
            Drop("homework 01", reason="Illness."),
            ForgiveLate("homework 02", reason="Family emergency.")
        ])

    """
    if isinstance(student, str):
        student = gradebook.students.find(student)

    for exception in exceptions:
        exception(gradebook, student)


# ForgiveLate --------------------------------------------------------------------------


class ForgiveLate:
    """Forgive a student's late assignment. To be used with :func:`make_exceptions`.

    Parameters
    ----------
    assignment : str
        The name of the assignment whose lateness will be forgiven.

    reason: Optional[str]
        An optional reason for the exception.

    """

    def __init__(self, assignment: str, reason: Optional[str] = None):
        self.assignment = assignment
        self.reason = reason

    def __call__(self, gradebook: Gradebook, student: Student):
        gradebook.lateness.loc[student, self.assignment] = _pd.Timedelta(0, "s")

        msg = f"Exception applied: late {self.assignment.title()} is forgiven."
        msg = _add_reason_to_message(msg, self.reason)

        gradebook.add_note(student, "lates", msg)


# Drop ---------------------------------------------------------------------------------


class Drop:
    """Drop a student's assignment. To be used with :func:`make_exceptions`.

    Parameters
    ----------
    assignment : str
        The name of the assignment that will be dropped.

    reason: Optional[str]
        An optional reason for the exception.

    """

    def __init__(self, assignment: str, reason: Optional[str] = None):
        self.assignment = assignment
        self.reason = reason

    def __call__(self, gradebook: Gradebook, student: Student):
        gradebook.dropped.loc[student, self.assignment] = True

        msg = f"Exception applied: {self.assignment.title()} dropped."
        msg = _add_reason_to_message(msg, self.reason)
        gradebook.add_note(student, "drops", msg)


# Replace ------------------------------------------------------------------------------


class Replace:
    """Replace a student's score on an assignment. To be used with :func:`make_exceptions`.

    Parameters
    ----------
    assignment : str
        The name of the assignment whose score will be replaced.

    with_ : Union[str, Points, Percentage]
        If a string, it will be interpreted as the name of an assignment, and
        that assignment's score will be used to replace the given assignment's
        score. If :class:`Points`, this will override the existing point total.
        If :class:`Percentage`, the new point total is computed from the points
        possible for the assignment.

    reason: Optional[str]
        An optional reason for the exception.

    """

    def __init__(
        self,
        assignment: str,
        with_: Union[str, Points, Percentage],
        reason: Optional[str] = None,
    ):
        self.assignment = assignment
        self.with_ = with_
        self.reason = reason

    def __call__(self, gradebook: Gradebook, student: Student):
        if isinstance(self.with_, str):
            other_assignment_score = (
                gradebook.points_earned.loc[student, self.with_]
                / gradebook.points_possible.loc[self.with_]
            )
            amount = Percentage(other_assignment_score * 100)
            msg = f"Replacing score on {self.assignment.title()} with score on {self.with_.title()}."
        else:
            # the amount has been explicitly given
            amount = self.with_
            msg = f"Overriding score on {self.assignment.title()} to be {amount}."

        new_points = _convert_amount_to_absolute_points(
            amount, gradebook, self.assignment
        )

        gradebook.points_earned.loc[student, self.assignment] = new_points

        msg = _add_reason_to_message(msg, self.reason)
        gradebook.add_note(student, "misc", msg)
