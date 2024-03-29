import itertools
from typing import Optional, Collection

import pandas as _pd

from ..core import Gradebook


def drop_most_favorable(
    gradebook: Gradebook, n: int, within: Optional[Collection[str]] = None
):
    """Drop the lowest `n` grades within a group of assignments.

    If all assignments are worth the same number of points, dropping the
    assignment with the lowest score is most advantageous to the student.
    However, if the assignments are not worth the same number of points, the
    best strategy for the student is not necessarily to drop to assignment with
    the smallest score. In this case, the problem of determining the optimal
    set of assignments to drop in order to maximize the overall score is
    non-trivial.

    In this implementation, dropping assignments is performed via a brute-force
    algorithm: each possible combination of kept assignments is tested, and the
    one which yields the largest total_points / maximum_points_possible is
    used. The time complexity of this approach is combinatorial, and therefore
    it is not recommended beyond small problem sizes. For a better algorithm,
    see: http://cseweb.ucsd.edu/~dakane/droplowest.pdf

    If an assignment has already been marked as dropped, it won't be considered
    for dropping. This is useful, for instance, when a student's assignment is
    dropped due to an external circumstance.

    Modifies the input gradebook.

    Parameters
    ----------
    gradebook : Gradebook
        The gradebook that will be modified.
    n : int
        The number of grades to drop.
    within : Optional[Collection[str]]
        A collection of assignment names; the lowest score among them will be
        dropped. If None, all assignments will be used. Default: None

    Raises
    ------
    ValueError
        If `within` is empty, or if n is not a positive integer.

    """
    if within is None:
        within = gradebook.assignments

    # the combinations of assignments to drop
    combinations = list(itertools.combinations(within, n))

    # we'll repeatedly replace this gradebook's dropped attribute
    testbed = gradebook.copy()

    # we will try each combination and compute the resulting score for each student
    scores = []
    for possibly_dropped in combinations:
        testbed.dropped = gradebook.dropped.copy()
        testbed.dropped.loc[:, possibly_dropped] = True
        scores.append(testbed.overall_score)

    # now we put the scores into a table and find the index of the best
    # score for each student
    all_scores = _pd.concat(scores, axis=1)
    index_of_best_score = all_scores.idxmax(axis=1)

    # loop through the students and mark the assignments which should be
    # dropped
    new_dropped = gradebook.dropped.copy()
    for student in gradebook.students:
        best_combo_ix = index_of_best_score.loc[student]
        tossed = list(combinations[best_combo_ix])
        new_dropped.loc[student, tossed] = True

        for assignment in tossed:
            gradebook.add_note(student, "drops", f"{assignment.title()} dropped.")

    gradebook.dropped = new_dropped
