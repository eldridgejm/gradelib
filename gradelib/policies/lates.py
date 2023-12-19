import typing
from typing import Optional, Sequence, Union, Callable

from ..core import Percentage, Points, Gradebook, Student


class LateInfo(typing.NamedTuple):
    """Contains information about a single late assignment.

    Attributes
    ----------
    gradebook : Gradebook
        The gradebook containing the late assignment.
    student : Student
        The student who submitted the late assignment.
    assignment : str
        The name of the late assignment.
    number : int
        The number of late assignments submitted by the student that have been
        seen so far, including this one.

    """

    gradebook: Gradebook
    student: Student
    assignment: str
    number: int


Penalty = Optional[Union[Points, Percentage]]
"""A type alias for a penalty returned by a late policy.

This can be a fixed number of points (:class:`gradelib.Points`), a percentage of the
total points possible (:class:`gradelib.Percentage`), or ``None`` to indicate that no
penalty should be applied.

"""


class Deduct:
    """A late policy that deducts a fixed amount from the grade.

    Parameters
    ----------
    amount : Union[Points, Percentage]
        The amount to deduct from the grade. This can be a fixed number of
        points, or a percentage of the total points possible.

    """

    def __init__(self, amount: Union[Points, Percentage]):
        self.amount = amount

    def __call__(self, _: LateInfo) -> Penalty:
        return self.amount


class Forgive:
    """A late policy that forgives the first N late assignments.

    Parameters
    ----------
    number : int
        The number of late assignments to forgive.
    then : Callable[[LateInfo], Penalty]
        The policy to apply to late assignments after the first N.
        By default, this is a policy that deducts 100% of the points.

    """

    def __init__(
        self, number: int, then: Callable[[LateInfo], Penalty] = Deduct(Percentage(100))
    ):
        self.number = number
        self.then = then

    def __call__(self, info: LateInfo) -> Penalty:
        if info.number <= self.number:
            # forgive this late
            forgiveness_left = self.number - info.number
            message = (
                f"Late forgiveness #{info.number} used on "
                f"{info.assignment.title()}. Late forgiveness remaining: {forgiveness_left}."
            )
            info.gradebook.add_note(info.student, "lates", message)
            return None
        else:
            return self.then(info)


def penalize(
    gradebook: Gradebook,
    within: Optional[Sequence[str]] = None,
    policy: Callable[[LateInfo], Penalty] = Deduct(Percentage(100)),
    order_by: Union[
        str, Callable[[Gradebook, Student, Sequence[str]], Sequence[str]]
    ] = "value",
):
    """Penalize late assignments.

    Parameters
    ----------
    gradebook : Gradebook
        The gradebook containing the assignments.
    within : Optional[Sequence[str]]
        The assignments within which to look for late submissions. If None,
        all assignments will be considered.
    policy : Callable[[LateInfo], Penalty]
        The policy to apply to late assignments. This should be a function that
        accepts a :class:`LateInfo` object and returns a :class:`Penalty` object.
        By default, this is a policy that deducts 100% of the points for any
        late assignment. For alternative policies, see :class:`Deduct` and
        :class:`Forgive`.
    order_by : Union[str, Callable[[Gradebook, Student, Sequence[str]], Sequence[str]]]
        Determines the order in which assignments are considered (e.g., disambiguates
        what is meant by "first late assignment"). By default, this is "value",
        which means that assignments will be considered in order of decreasing
        value. Also accepted is "index", which means that assignments will be
        considered in the order in which they appear in ``within``. Finally,
        a function can be passed that accepts a gradebook, a student, and the
        sequence of assignments determined by the ``within`` argument, and
        returns a sequence of assignments in the order in which they should be
        considered.

    """
    if within is None:
        within = gradebook.assignments

    if not within:
        raise ValueError("Must have at least one assignment to penalize.")

    def _penalize_lates_for(student: Student):
        number = 0

        # by default, reorder assignments from most valuable to least valuable,
        # since forgiveness will be given to most valuable assignments first
        if order_by == "value":
            value = gradebook.value[within].loc[student].sort_values(ascending=False)
            ordered_assignments = value.index
        elif order_by == "index":
            ordered_assignments = within
        elif callable(order_by):
            ordered_assignments = order_by(gradebook, student, within)
        else:
            raise ValueError(f"Unknown order_by value: {order_by}")

        late = gradebook.late.loc[student]
        for assignment in ordered_assignments:
            if late[assignment]:
                if gradebook.dropped.loc[student, assignment]:
                    continue
                else:
                    number += 1
                    penalty = policy(LateInfo(gradebook, student, assignment, number))
                    if penalty is not None:
                        _apply_penalty(gradebook, student, assignment, penalty)

    for student in gradebook.students:
        _penalize_lates_for(student)


def _apply_penalty(
    gradebook: Gradebook,
    student: Student,
    assignment: str,
    deduction: Union[Points, Percentage],
):
    """A helper function that applies a penalty to a late assignment."""
    pts = gradebook.points_earned.loc[student, assignment]
    if isinstance(deduction, Points):
        new_point_total = pts - deduction.amount
    elif isinstance(deduction, Percentage):
        # percentage deduction is of points earned, not points possible
        new_point_total = pts - (deduction.amount / 100) * pts
    else:
        raise TypeError("Unknown deduction type.")

    message = f"{assignment.title()} late. Deduction: {deduction}. Points earned: {new_point_total}"
    gradebook.add_note(student, "lates", message)

    gradebook.points_earned.loc[student, assignment] = new_point_total
