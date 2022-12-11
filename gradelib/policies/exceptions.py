import itertools
import collections

import numpy as np
import pandas as pd

from ..core import Percentage, Points
from .._common import resolve_assignment_grouper


def _empty_mask_like(table):
    """Given a dataframe, create another just like it with every entry False."""
    empty = table.copy()
    empty.iloc[:, :] = False
    return empty.astype(bool)


# exceptions
# ======================================================================================


def make_exceptions(gradebook, students):
    for student, exceptions in students.items():
        for exception in exceptions:
            exception(gradebook, student)


class ForgiveLate:
    def __init__(self, assignment):
        self.assignment = assignment

    def __call__(self, gradebook, student):
        pid = gradebook.students.find(student)
        gradebook.lateness.loc[pid, self.assignment] = pd.Timedelta(0, "s")
        gradebook.add_note(
            pid,
            "lates",
            f"Exception applied: late {self.assignment.title()} is forgiven.",
        )
        return gradebook


class Drop:
    def __init__(self, assignment):
        self.assignment = assignment

    def __call__(self, gradebook, student):
        pid = gradebook.students.find(student)
        gradebook.dropped.loc[pid, self.assignment] = True
        gradebook.add_note(
            pid, "drops", f"Exception applied: {self.assignment.title()} dropped."
        )
        return gradebook


def _adjustment_from_difference(difference):
    if difference < 0:
        return Deduction(Points(-difference))
    else:
        return Addition(Points(difference))


class Replace:
    def __init__(self, assignment, with_):
        self.assignment = assignment
        self.with_ = with_

    def __call__(self, gradebook, student):
        pid = gradebook.students.find(student)
        current_points = gradebook.points_earned.loc[pid, self.assignment]
        other_assignment_score = (
            gradebook.points_earned.loc[pid, self.with_]
            / gradebook.points_possible.loc[self.with_]
        )
        new_points = (
            other_assignment_score * gradebook.points_possible.loc[self.assignment]
        )

        gradebook.points_earned.loc[pid, self.assignment] = new_points
        gradebook.add_note(
            pid,
            "misc",
            f"Replacing {self.assignment.title()} with {self.with_.title()}.",
        )
        return gradebook


def _convert_amount_to_absolute_points(amount, gradebook, assignment):
    if isinstance(amount, Points):
        return amount.amount
    else:
        # calculate percentage adjustment based on points possible
        return amount.amount * gradebook.points_possible.loc[assignment]


class Override:
    def __init__(self, assignment, amount):
        self.assignment = assignment
        self.amount = amount

    def __call__(self, gradebook, student):
        pid = gradebook.students.find(student)
        current_points = gradebook.points_earned.loc[pid, self.assignment]
        new_points = _convert_amount_to_absolute_points(
            self.amount, gradebook, self.assignment
        )
        gradebook.points_earned.loc[pid, self.assignment] = new_points
        gradebook.add_note(
            pid,
            "misc",
            f"Manually set {self.assignment} to {new_points} points as part of an exception.",
        )
        return gradebook
