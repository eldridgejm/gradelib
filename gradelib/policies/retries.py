from typing import Union, Sequence, Callable, Mapping

import pandas as _pd


from ..core import Gradebook, Student


def _fmt_as_pct(f):
    return f"{f * 100:0.2f}%"


class Maximum:
    """The maximum score on a set of assignments."""

    def __call__(self, gradebook: Gradebook, assignments: Sequence[str]) -> _pd.Series:
        max_assignment_ix = gradebook.score.loc[:, assignments].idxmax(axis=1)
        max_score = gradebook.score[assignments].max(axis=1)
        self._add_notes(gradebook, assignments, max_assignment_ix)
        return max_score

    def _add_notes(
        self,
        gradebook: Gradebook,
        assignments: Sequence[str],
        max_assignment_ix: _pd.Series,
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
            gradebook.add_note(student, "retries", make_note_for(student))


def take_best_attempt(
    gradebook: Gradebook,
    attempts: Mapping[str, Sequence[str]],
    *,
    remove=False,
    policy: Callable[[Gradebook, Sequence[str]], _pd.Series] = Maximum(),
    points_possible: Union[int, float] = 1.0,
):
    """Provides multiple chances to earn points on an assignment.

    Parameters
    ----------
    gradebook : Gradebook
        The gradebook that will be modified.
    attempts : Mapping[str, Sequence[str]]
        A mapping from the name of the new assignment to a sequence of
        existing assignments that will be used to determine the score on
        the new assignment.
    remove : bool, optional
        Whether to remove the existing assignments, by default False.
    policy : Callable[[Gradebook, Sequence[str]], pd.Series], optional
        A function that takes a gradebook and a sequence of assignment names
        and returns a Series of scores, by default Maximum().
    points_possible : Union[int, float], optional
        The number of points possible on the new assignment, by default 1.

    """
    for new_assignment, existing_assignments in attempts.items():
        redeemed_score = policy(gradebook, existing_assignments)
        points_earned = redeemed_score * points_possible
        gradebook.add_assignment(new_assignment, points_earned, points_possible)

        if remove:
            gradebook.remove_assignments(existing_assignments)
