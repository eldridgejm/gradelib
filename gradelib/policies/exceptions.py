from collections.abc import Mapping, Sequence
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

    students
        A mapping from student names to a list of exceptions that will be
        applied. The exceptions should be instances of :class:`ForgiveLate`,
        :class:`Drop`, or :class:`Replace`. The keys can be the full name
        or identifying substrings of names -- if it is not a precise match
        (more than one student is found), an exception will be raised.

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

        gradebook.add_note(student.pid, "lates", msg)


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
        gradebook.add_note(student.pid, "drops", msg)


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
        gradebook.add_note(student.pid, "misc", msg)
