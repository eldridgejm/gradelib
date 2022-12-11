import collections

from ..core import Percentage, Points
from ._common import resolve_within

_LateInfo = collections.namedtuple("LateInfo", "gradebook pid assignment number")


class PenalizeLates:
    """Penalize late assignments.

    Adds deductions to the gradebook by modifying it.

    Parameters
    ----------
    forgive : Optional[int]
        The number of lates to forgive. Default: 0
    within : Optional[Within]
        A sequence of assignments within which lates will be forgiven, or a
        callable producing such a sequence of assignments. If None, all
        assignments will be used. Default: None
    deduction : Optional[Union[Points, Percentage, Callable]]
        The amount that should be deducted. See the Notes for instructions
        on using a callable. If None, 100% is deducted.
    order_by : str
        One of {'value', 'index'}. If 'value', highly-valued assignments are
        forgiven first. If 'index', assignments are forgiven in the order they
        appear in `within`. Default: 'value'.

    Notes
    -----
    The first `forgive` late assignments are forgiven. By "first", we mean with
    respect to the order specified by the `within` argument. As such, the
    `within` argument must be an ordered *sequence*. If not, a ValueError will
    be raised. For convenience, the result of :attr:`Gradebook.assignments` is
    an ordered sequence, and the order is guaranteed to be the same as the
    order of the underlying column names in the `points` table.

    If a late assignment is marked as dropped it will not be forgiven, as
    it is advantageous for the student to use the forgiveness elsewhere.

    `deduction` can be a callable, in which case it is called with a namedtuple
    with the following attributes:

        - `gradebook`: the current gradebook
        - `assignment`: the current assignment
        - `pid`: the pid of the student being penalized
        - `number`: the number of late assignments seen so far that have not
          been forgiven, including the current assignment

    It should return either a Points or Percentage object. This is a very
    general scheme, and allows penalizing based on the lateness of the
    assignment, for example.

    Raises
    ------
    ValueError
        If `within` is empty, or if forgive is negative.
    TypeError
        If `within` is not an ordered sequence.

    """

    def __init__(
        self, within=None, forgive=0, deduction=Percentage(1), order_by="value"
    ):
        self.within = within
        self.forgive = forgive
        self.deduction = deduction
        self.order_by = order_by

    def __call__(self, gradebook):
        if self.forgive < 0:
            raise ValueError("Must forgive a non-negative number of lates.")

        within = resolve_within(gradebook, self.within)

        def _penalize_lates_for(pid):
            forgiveness_left = self.forgive
            number = 0

            # by default, reorder assignments from most valuable to least valuable,
            # since forgiveness will be given to most valuable assignments first
            if self.order_by == "value":
                value = gradebook.value[within].loc[pid]
                sorted_assignments = sorted(
                    within, key=lambda a: value[a], reverse=True
                )
            else:
                sorted_assignments = self.within

            late = gradebook.late.loc[pid]
            for assignment in sorted_assignments:
                if late[assignment]:
                    if gradebook.dropped.loc[pid, assignment]:
                        continue
                    if forgiveness_left > 0:
                        # forgiven
                        forgiveness_left -= 1
                        message = (
                            f"Slip day #{self.forgive - forgiveness_left} used on "
                            f"{assignment.title()}. Slip days remaining: {forgiveness_left}."
                        )
                        gradebook.add_note(pid, "lates", message)
                    else:
                        number += 1
                        self._deduct(gradebook, pid, assignment, number)

        for student in gradebook.students:
            _penalize_lates_for(student)

        return gradebook

    def _deduct(self, gradebook, pid, assignment, number):
        if callable(self.deduction):
            info = _LateInfo(gradebook, pid, assignment, number)
            d = self.deduction(info)
        else:
            d = self.deduction

        pts = gradebook.points_earned.loc[pid, assignment]
        if isinstance(d, Points):
            new_point_total = pts - d.amount
        elif isinstance(d, Percentage):
            new_point_total = pts - d.amount * pts

        message = (
            f"{assignment.title()} late. Deduction: {d}. Points earned: {new_point_total}."
        )
        gradebook.add_note(pid, "lates", message)

        gradebook.points_earned.loc[pid, assignment] = new_point_total
