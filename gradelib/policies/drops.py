import itertools

import pandas as pd

from ._common import resolve_within


def drop_lowest(gradebook, n, within=None):
    """Drop the lowest n grades within a group of assignments.

    Modifies the input gradebook.

    Parameters
    ----------
    n : int
        The number of grades to drop.
    within : Optional[Within]
        A collection of assignments; the lowest among them will be dropped. If
        a callable, it will be called on the gradebook's assignments to produce
        such a collection. If None, all assignments will be used. Default: None

    Notes
    -----
    If all assignments are worth the same number of points, dropping the
    assignment with the lowest score is most advantageous to the student.
    However, if the assignments are not worth the same number of points, the
    best strategy for the student is not necessarily to drop to assignment with
    the smallest score. In this case, the problem of determining the optimal
    set of assignments to drop in order to maximize the overall score is
    non-trivial.

    In this implementation, dropping assignments is performed via a
    brute-force algorithm: each possible combination of kept assignments is
    tested, and the one which yields the largest total_points /
    maximum_points_possible is used. The time complexity of this approach
    is combinatorial, and therefore it is not recommended beyond small
    problem sizes. For a better algorithm, see:
    http://cseweb.ucsd.edu/~dakane/droplowest.pdf

    If an assignment has deductions for whatever reason, those deductions will
    be applied before calculating which assignments to drop. For that reason,
    it is usually best to apply whatever deductions are needed before using
    this.

    If an assignment has already been marked as dropped, it won't be
    considered for dropping. This is useful, for instance, when a student's
    assignment is dropped due to an external circumstance.

    Raises
    ------
    ValueError
        If `within` is empty, or if n is not a positive integer.

    """
    # number of kept assignments
    within = resolve_within(gradebook, within)

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
    all_scores = pd.concat(scores, axis=1)
    index_of_best_score = all_scores.idxmax(axis=1)

    # loop through the students and mark the assignments which should be
    # dropped
    new_dropped = gradebook.dropped.copy()
    for pid in gradebook.pids:
        best_combo_ix = index_of_best_score.loc[pid]
        tossed = list(combinations[best_combo_ix])
        new_dropped.loc[pid, tossed] = True

        for assignment in tossed:
            gradebook.add_note(pid, "drops", f"{assignment} dropped.")

    gradebook.dropped = new_dropped
