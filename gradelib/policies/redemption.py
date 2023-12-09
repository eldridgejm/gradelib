from typing import Union, Sequence, Callable

import pandas as pd


from ..core import Gradebook, Student


def _fmt_as_pct(f):
    return f"{f * 100:0.2f}%"


class Maximum:
    """Perform redemption by taking the maximum score of a set of assignments.

    Adds a note to each student's gradebook entry describing the redemption.

    """

    def __call__(self, gradebook: Gradebook, assignments: Sequence[str]) -> pd.Series:
        max_assignment_ix = gradebook.score[assignments].idxmax(axis=1)
        max_score = gradebook.score[assignments].max(axis=1)
        self._add_notes(gradebook, assignments, max_assignment_ix)
        return max_score

    def _add_notes(
        self,
        gradebook: Gradebook,
        assignments: Sequence[str],
        max_assignment_ix: pd.Series,
    ):
        def make_note_for(student: Student) -> str:
            def assignment_part(assignment):
                """Make string like 'Mt01 score: 95.00%'."""
                formatted_score = _fmt_as_pct(gradebook.score.loc[student, assignment])
                return f"{assignment.title()} score: {formatted_score}."

            # makes string like 'Mt01 score used.'
            used_part = f"{max_assignment_ix.loc[student].title()} score used."

            return " ".join([assignment_part(a) for a in assignments] + [used_part])

        for student in gradebook.students:
            gradebook.add_note(student, "redemption", make_note_for(student))


def redeem(
    gradebook: Gradebook,
    existing_assignments: Sequence[str],
    new_assignment: str,
    *,
    remove=False,
    policy: Callable[[Gradebook, Sequence[str]], pd.Series] = Maximum(),
    points_possible: Union[int, float] = 1.0,
):
    """Provides multiple chances to earn points on an assignment.

    Parameters
    ----------
    gradebook : Gradebook
        The gradebook that will be modified.
    existing_assignments : Sequence[str]
        The assignments to be aggregated.
    new_assignment : str
        The name of the assignment that will be created.
    remove : bool, optional
        Whether to remove the existing assignments, by default False.
    policy : Callable[[Gradebook, Sequence[str]], pd.Series], optional
        A function that takes a gradebook and a sequence of assignment names
        and returns a Series of scores, by default Maximum().
    points_possible : Union[int, float], optional
        The number of points possible on the new assignment, by default 1.

    """
    redeemed_score = policy(gradebook, existing_assignments)
    points_earned = redeemed_score * points_possible
    gradebook.add_assignment(new_assignment, points_earned, points_possible)

    if remove:
        gradebook.remove_assignments(existing_assignments)
