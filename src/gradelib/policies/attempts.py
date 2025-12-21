from collections.abc import Callable, Mapping, Sequence

import pandas as _pd

from ..core import Gradebook


def _fmt_as_pct(f):
    return f"{f * 100:0.2f}%"


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
                f"{str(assignment).title()} raw score: {raw_score}, "
                f"after penalty for retrying: {effective_score}."
            )

    # if all of a student's attempts are nans (i.e. they didn't attempt any of the
    # parts), .idxmax() will fail with a ValueError (or print a warning). In this case,
    # there really is no "best" assignment, so we won't print anything more.
    if not bool(effective_scores.isna().all()):
        best_assignment = str(effective_scores.idxmax())
        best_score = _fmt_as_pct(effective_scores.max())
        parts.append(f"{best_assignment.title()} score ({best_score}) used.")

    return " ".join(parts)


def _no_penalty_policy(scores: _pd.Series) -> _pd.Series:
    return scores


# lateness policies ====================================================================


def max_lateness(latenesses: _pd.Series, _: str) -> _pd.Timedelta:
    """Returns the maximum lateness across all attempts.

    The overall assignment's lateness will be the largest lateness value among all
    attempts. This is the most conservative approach: if any attempt is late, the
    overall assignment will be considered late with that maximum lateness amount.

    """
    return latenesses.max()


def min_lateness(latenesses: _pd.Series, _: str) -> _pd.Timedelta:
    """Returns the minimum lateness across all attempts.

    The overall assignment's lateness will be the smallest lateness value among all
    attempts. If any attempt is on-time (lateness = 0), the overall will be on-time.
    The overall assignment will only be considered late if all attempts are late, in
    which case it takes the smallest lateness amount.

    """
    return latenesses.min()


def lateness_of_best(latenesses: _pd.Series, best_attempt: str) -> _pd.Timedelta:
    """Returns the lateness of the best attempt."""
    return latenesses.loc[best_attempt]


# take_best() ==========================================================================


def take_best(
    gradebook: Gradebook,
    attempts: Mapping[str, Sequence[str]],
    *,
    remove=True,
    penalty_strategy: Callable[[_pd.Series], _pd.Series] | None = None,
    lateness_strategy: Callable[[_pd.Series, str], _pd.Timedelta] = max_lateness,
    points_possible: int | float = 1.0,
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
    penalty_strategy : Optional[Callable[[pd.Series], pd.Series]], optional
        A function that takes a Series of the student's previous scores and returns a
        Series of the effective scores after applying any penalties. The index of the
        new Series should match that of the input Series. A value of ``None`` indicates
        that no penalties should be applied; this is the default.
    lateness_strategy : Callable[[pd.Series, str], pd.Timedelta], optional
        A function that determines the overall lateness of the new assignment based on
        the lateness of individual attempts. The function takes two arguments: a Series
        of Timedelta objects (one per attempt) and a string indicating which attempt was
        selected as best. It returns a single Timedelta representing the overall
        lateness.

        Built-in strategies:

        - :func:`max_lateness` (default): Returns the maximum lateness across all attempts
        - :func:`lateness_of_best`: Returns the lateness of whichever attempt scored best
        - :func:`min_lateness`: Returns the minimum lateness across all attempts

        Default: :func:`max_lateness`
    points_possible : Union[int, float], optional
        The number of points possible on the new assignment, by default 1.

    """
    if penalty_strategy is None:
        penalty_strategy = _no_penalty_policy

    for new_assignment, existing_assignments in attempts.items():
        best_scores = _pd.Series(dtype="float64")
        latenesses = _pd.Series(dtype="timedelta64[s]")
        for student in gradebook.students:
            raw_attempt_scores = gradebook.score.loc[student, existing_assignments]
            effective_attempt_scores = penalty_strategy(raw_attempt_scores)

            gradebook.add_note(
                student,
                "attempts",
                _make_notes(raw_attempt_scores, effective_attempt_scores),
            )

            # best_attempt will be the name of the assignment representing the best
            # attempt
            best_attempt = effective_attempt_scores.idxmax()
            assert isinstance(best_attempt, str)

            best_scores[student] = effective_attempt_scores.loc[best_attempt]

            latenesses.loc[student] = lateness_strategy(
                gradebook.lateness.loc[student, existing_assignments], best_attempt
            )

        points_earned = best_scores * points_possible
        gradebook.add_assignment(
            new_assignment, points_earned, points_possible, lateness=latenesses
        )

        if remove:
            gradebook.remove_assignments(existing_assignments)
