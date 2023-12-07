import typing
from typing import Optional, Sequence, Union, Callable

from ..core import Percentage, Points, Gradebook, Student


class LateInfo(typing.NamedTuple):
    gradebook: Gradebook
    student: Student
    assignment: str
    number: int


Penalty = Union[Points, Percentage, None]


class Deduct:
    def __init__(self, amount: Union[Points, Percentage]):
        self.amount = amount

    def __call__(self, _: LateInfo) -> Penalty:
        return self.amount


class Forgive:
    def __init__(
        self, number: int, then: Callable[[LateInfo], Penalty] = Deduct(Percentage(1))
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
    policy: Callable[[LateInfo], Penalty] = Deduct(Percentage(1)),
    order_by="value",
):
    if within is None:
        within = gradebook.assignments

    if not within:
        raise ValueError("Must have at least one assignment to penalize.")

    def _penalize_lates_for(student: Student):
        number = 0

        # by default, reorder assignments from most valuable to least valuable,
        # since forgiveness will be given to most valuable assignments first
        if order_by == "value":
            value = gradebook.value[within].loc[student]
            sorted_assignments = sorted(within, key=lambda a: value[a], reverse=True)
        else:
            sorted_assignments = within

        late = gradebook.late.loc[student]
        for assignment in sorted_assignments:
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
    pts = gradebook.points_earned.loc[student, assignment]
    if isinstance(deduction, Points):
        new_point_total = pts - deduction.amount
    elif isinstance(deduction, Percentage):
        # percentage deduction is of points earned, not points possible
        new_point_total = pts - deduction.amount * pts
    else:
        raise TypeError("Unknown deduction type.")

    message = f"{assignment.title()} late. Deduction: {deduction}. Points earned: {new_point_total}."
    gradebook.add_note(student, "lates", message)

    gradebook.points_earned.loc[student, assignment] = new_point_total
