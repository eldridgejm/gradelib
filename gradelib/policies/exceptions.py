import itertools
import collections

import numpy as np
import pandas as pd

from ..core import Percentage, Points
from .._common import resolve_assignment_grouper


# private helpers ----------------------------------------------------------------------


def _empty_mask_like(table):
    """Given a dataframe, create another just like it with every entry False."""
    empty = table.copy()
    empty.iloc[:, :] = False
    return empty.astype(bool)


def _add_reason_to_message(message, reason):
    if reason is not None:
        message += ' Reason: ' + reason
    return message


def _convert_amount_to_absolute_points(amount, gradebook, assignment):
    if isinstance(amount, Points):
        return amount.amount
    else:
        # calculate percentage adjustment based on points possible
        return amount.amount * gradebook.points_possible.loc[assignment]


# public functions and classes =========================================================


def make_exceptions(gradebook, students):
    """Make policy exceptions for individual students.

    Parameters
    ----------
    gradebook : Gradebook
        The gradebook to apply the exceptions to. Will be modified.

    students
        A mapping from students to a list of exceptions that will be applied.
        The exceptions should be instances of :class:`ForgiveLate`,
        :class:`Drop`, or :class:`Replace`

    """
    for student, exceptions in students.items():
        for exception in exceptions:
            exception(gradebook, student)


class ForgiveLate:
    """Forgive a student's late assignment. To be used with :func:`make_exceptions`.

    Parameters
    ----------
    assignment : str
        The name of the assignment whose lateness will be forgiven.

    reason: Optional[str]
        An optional reason for the exception.

    """
    def __init__(self, assignment, reason=None):
        self.assignment = assignment
        self.reason = reason

    def __call__(self, gradebook, student):
        pid = gradebook.students.find(student)
        gradebook.lateness.loc[pid, self.assignment] = pd.Timedelta(0, "s")

        msg = f"Exception applied: late {self.assignment.title()} is forgiven."
        msg = _add_reason_to_message(msg, self.reason)

        gradebook.add_note(
            pid,
            "lates",
            msg
        )
        return gradebook


class Drop:
    """Drop a student's assignment. To be used with :func:`make_exceptions`.

    Parameters
    ----------
    assignment : str
        The name of the assignment that will be dropped.

    reason: Optional[str]
        An optional reason for the exception.

    """
    def __init__(self, assignment, reason=None):
        self.assignment = assignment
        self.reason = reason

    def __call__(self, gradebook, student):
        pid = gradebook.students.find(student)
        gradebook.dropped.loc[pid, self.assignment] = True

        msg = f"Exception applied: {self.assignment.title()} dropped."
        msg = _add_reason_to_message(msg, self.reason)
        gradebook.add_note(
            pid, "drops", msg
        )
        return gradebook


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
    def __init__(self, assignment, with_, reason=None):
        self.assignment = assignment
        self.with_ = with_
        self.reason = reason

    def __call__(self, gradebook, student):
        pid = gradebook.students.find(student)

        if isinstance(self.with_, str):
            other_assignment_score = (
                gradebook.points_earned.loc[pid, self.with_]
                / gradebook.points_possible.loc[self.with_]
            )
            amount = Percentage(other_assignment_score)
            msg = f"Replacing score on {self.assignment.title()} with score on {self.with_.title()}."
        else:
            # the amount has been explicitly given
            amount = self.with_
            msg = f'Overriding score on {self.assignment.title()} to be {amount}.'

        new_points = _convert_amount_to_absolute_points(
            amount, gradebook, self.assignment
        )

        gradebook.points_earned.loc[pid, self.assignment] = new_points

        msg = _add_reason_to_message(msg, self.reason)
        gradebook.add_note(
            pid,
            "misc",
            msg
        )
        return gradebook
