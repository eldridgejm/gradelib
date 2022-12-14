from __future__ import annotations

import collections
import typing

from ..core import Percentage, Points
from ..core.assignments import AssignmentSelector
from .._common import resolve_assignment_selector

_LateInfo = collections.namedtuple("LateInfo", "gradebook pid assignment number")


def penalize_lates(
    gradebook: Gradebook,
    within: typing.Optional[AssignmentSelector] = None,
    forgive=0,
    deduction=Percentage(1),
    order_by="value",
):
    """Penalize late assignments.

    The first `forgive` late assignments are forgiven. By "first", we mean with
    respect to the order specified by the `within` argument. As such, the
    `within` argument must be an ordered *sequence*. If not, a ValueError will
    be raised. For convenience, the result of :attr:`Gradebook.assignments` is
    an ordered sequence, and the order is guaranteed to be the same as the
    order of the underlying column names in the `points` table.

    If a late assignment is marked as dropped it will not be forgiven, as
    it is advantageous for the student to use the forgiveness elsewhere.

    If the `deduction` is an instance of :class:`Percentage`, the deduction is
    calculated by multuplying the percentage by the points previously earned,
    as opposed to the points possible. Therefore, if a student had earned 50
    out of 60 points on an assignment, a 50% deduction would leave them with 25
    points.

    `deduction` can be a callable, in which case it is called with a namedtuple
    with the following attributes:

        - `gradebook`: the current gradebook
        - `assignment`: the current assignment
        - `pid`: the pid of the student being penalized
        - `number`: the number of late assignments seen so far that have not
          been forgiven, including the current assignment

    It should return either a :class:`gradelib.Points` or
    :class:`gradelib.Percentage` object. This is a very general scheme, and
    allows penalizing based on the lateness of the assignment, for example.

    Modifies the gradebook given as input.

    Parameters
    ----------
    gradebook : Gradebook
        The gradebook that will be modified.
    forgive : Optional[int]
        The number of lates to forgive. Default: 0
    within : Optional[AssignmentSelector]
        A sequence of assignments within which lates will be forgiven, or a
        callable producing such a sequence of assignments. If None, all
        assignments will be used. Default: None
    deduction : Optional[Union[Points, Percentage, Callable]]
        The amount that should be deducted. See the Notes for instructions
        on using a callable. If None, 100% is deducted.
    order_by : str
        One of ``{'value', 'index'}``. If `value`, highly-valued assignments
        are forgiven first. If `index`, assignments are forgiven in the order
        they appear in `within`. Default: `value`.

    Raises
    ------
    ValueError
        If `within` is empty, or if forgive is negative.
    TypeError
        If `within` is not an ordered sequence.

    """
    if forgive < 0:
        raise ValueError("Must forgive a non-negative number of lates.")

    within = resolve_assignment_selector(within, gradebook.assignments)

    def _penalize_lates_for(pid):
        forgiveness_left = forgive
        number = 0

        # by default, reorder assignments from most valuable to least valuable,
        # since forgiveness will be given to most valuable assignments first
        if order_by == "value":
            value = gradebook.value[within].loc[pid]
            sorted_assignments = sorted(within, key=lambda a: value[a], reverse=True)
        else:
            sorted_assignments = within

        late = gradebook.late.loc[pid]
        for assignment in sorted_assignments:
            if late[assignment]:
                if gradebook.dropped.loc[pid, assignment]:
                    continue
                if forgiveness_left > 0:
                    # forgiven
                    forgiveness_left -= 1
                    message = (
                        f"Slip day #{forgive - forgiveness_left} used on "
                        f"{assignment.title()}. Slip days remaining: {forgiveness_left}."
                    )
                    gradebook.add_note(pid, "lates", message)
                else:
                    number += 1
                    _deduct(gradebook, pid, assignment, number, deduction)

    for student in gradebook.students:
        _penalize_lates_for(student)

    return gradebook


def _deduct(gradebook, pid, assignment, number, deduction):
    if callable(deduction):
        info = _LateInfo(gradebook, pid, assignment, number)
        d = deduction(info)
    else:
        d = deduction

    pts = gradebook.points_earned.loc[pid, assignment]
    if isinstance(d, Points):
        new_point_total = pts - d.amount
    elif isinstance(d, Percentage):
        # percentage deduction is of points earned, not points possible
        new_point_total = pts - d.amount * pts
    else:
        raise TypeError("Unknown deduction type.")

    message = (
        f"{assignment.title()} late. Deduction: {d}. Points earned: {new_point_total}."
    )
    gradebook.add_note(pid, "lates", message)

    gradebook.points_earned.loc[pid, assignment] = new_point_total