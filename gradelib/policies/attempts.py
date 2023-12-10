from typing import Union, Sequence, Callable, Mapping, Optional

import pandas as _pd


from ..core import Gradebook


def _fmt_as_pct(f):
    return f"{f * 100:0.2f}%"


def _scores_after_penalty(
    raw_scores: _pd.Series, policy: Callable[[int, float], float]
):
    """Apply a penalty policy to a series of scores."""
    return _pd.Series(
        [policy(i, score) for i, score in enumerate(raw_scores)], index=raw_scores.index
    )


def _make_notes(raw_scores: _pd.Series, effective_scores: _pd.Series) -> str:
    """Make a string to be used as a note for a student."""
    parts = []
    for assignment, raw_score, effective_score in zip(
        raw_scores.index, raw_scores, effective_scores
    ):
        raw_score = _fmt_as_pct(raw_score)
        effective_score = _fmt_as_pct(effective_score)
        if raw_score == effective_score:
            parts.append(f"{str(assignment).title()} score: {raw_score}.")
        else:
            parts.append(
                f"{str(assignment).title()} raw score: {raw_score}, after penalty for retrying: {effective_score}."
            )

    best_assignment = str(effective_scores.idxmax())
    best_score = _fmt_as_pct(effective_scores.max())
    parts.append(f"{best_assignment.title()} score ({best_score}) used.")

    return " ".join(parts)


def take_best(
    gradebook: Gradebook,
    attempts: Mapping[str, Sequence[str]],
    *,
    remove=True,
    policy: Optional[Callable[[int, float], float]] = None,
    points_possible: Union[int, float] = 1.0,
):
    """Replaces multiple attempts at an assignment with the best.

    Parameters
    ----------
    gradebook : Gradebook
        The gradebook that will be modified.
    attempts : Mapping[str, Sequence[str]]
        A mapping from the name of the new assignment to a sequence of
        existing assignments that will be used to determine the score on
        the new assignment.
    remove : bool, optional
        Whether to remove the existing assignments, by default True.
    policy : Optional[Callable[[int, float], float]]
        A function that takes an attempt number (with 0 being the first
        attempt) and a score and returns a new score. This can be used to
        penalize later attempts, for example. By default, the identity
        function is used.
    points_possible : Union[int, float], optional
        The number of points possible on the new assignment, by default 1.

    """
    if policy is None:
        policy = lambda _, score: score

    for new_assignment, existing_assignments in attempts.items():
        best_scores = _pd.Series()
        for student in gradebook.students:
            raw_attempt_scores = gradebook.score.loc[student, existing_assignments]
            effective_attempt_scores = _scores_after_penalty(raw_attempt_scores, policy)

            gradebook.add_note(
                student,
                "attempts",
                _make_notes(raw_attempt_scores, effective_attempt_scores),
            )

            best_scores[student] = effective_attempt_scores.max()

        points_earned = best_scores * points_possible
        gradebook.add_assignment(new_assignment, points_earned, points_possible)

        if remove:
            gradebook.remove_assignments(existing_assignments)
