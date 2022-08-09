import itertools
import collections

import numpy as np
import pandas as pd

from .core import Percentage, Points


def _empty_mask_like(table):
    """Given a dataframe, create another just like it with every entry False."""
    empty = table.copy()
    empty.iloc[:, :] = False
    return empty.astype(bool)


def _resolve_within(gradebook, within):
    if within is None:
        within = gradebook.assignments

    if callable(within):
        within = within(gradebook.assignments)

    if not within:
        raise ValueError("Cannot use an empty list of assignments.")

    return list(within)


# exceptions
# ======================================================================================

# policies
# ======================================================================================


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

    def __init__(self, within=None, forgive=0, deduction=Percentage(1)):
        self.within = within
        self.forgive = forgive
        self.deduction = deduction

    def __call__(self, gradebook):
        if self.forgive < 0:
            raise ValueError("Must forgive a non-negative number of lates.")

        within = _resolve_within(gradebook, self.within)

        def _penalize_lates_for(pid):
            forgiveness_left = self.forgive
            number = 0

            for assignment in within:
                if gradebook.late.loc[pid, assignment]:
                    if forgiveness_left > 0 and not gradebook.dropped.loc[pid, assignment]:
                        forgiveness_left -= 1
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

        gradebook.add_deduction(pid, assignment, d)


# DropLowest
# ======================================================================================


class DropLowest:
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

    def __init__(self, n, within=None):
        self.n = n
        self.within = within

    def __call__(self, gradebook):
        # number of kept assignments
        within = _resolve_within(gradebook, self.within)

        # the combinations of assignments to drop
        combinations = list(itertools.combinations(within, self.n))

        # count lates as zeros
        points_after_deductions = gradebook.points_after_deductions[within]

        # a full table of maximum points available. this will allow us to have
        # different points available per person
        points_possible = gradebook.points_marked.copy()[within]
        points_possible.iloc[:, :] = gradebook.points_possible[within].values

        # we will try each combination and compute the resulting score for each student
        scores = []
        for possibly_dropped in combinations:
            possibly_dropped = list(possibly_dropped)
            possibly_dropped_mask = gradebook.dropped.copy()
            possibly_dropped_mask[possibly_dropped] = True

            earned = points_after_deductions.copy()
            earned[possibly_dropped_mask] = 0

            out_of = points_possible.copy()
            out_of[possibly_dropped_mask] = 0

            score = earned.sum(axis=1) / out_of.sum(axis=1)
            scores.append(score)

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

        return gradebook._replace(dropped=new_dropped)

# Redemption
# ======================================================================================

class Redeem:

    def __init__(self, selector, remove_parts=False, deduction=None, suffix=' with redemption'):
        self.selector = selector
        self.remove_parts = remove_parts
        self.deduction = deduction
        self.suffix = suffix

    def __call__(self, gradebook):
        if isinstance(self.selector, dict):
            assignment_pairs = self.selector
        else:
            assignment_pairs = {}
            for prefix in self.selector:
                pair = [a for a in gradebook.assignments if a.startswith(prefix)]
                if len(pair) != 2:
                    raise ValueError(f'Prefix "{prefix}" does not match a pair of assignments.')
                assignment_pairs[prefix + self.suffix] = pair

        for new_name, assignment_pair in assignment_pairs.items():
            gradebook = self._redeem(gradebook, new_name, assignment_pair)

        if self.remove_parts:
            gradebook = self._remove_parts(gradebook)

        return gradebook

    def _redeem(self, gradebook, new_name, assignment_pair):
        first, second = assignment_pair

        if gradebook.dropped[[first, second]].values.any():
            raise ValueError("Cannot apply redemption to dropped assignments.")

        points_possible = gradebook.points_possible[[first, second]].max()

        first_scale, second_scale = points_possible / gradebook.points_possible[[first, second]]

        first_points = gradebook.points_after_deductions[first] * first_scale
        second_points = gradebook.points_after_deductions[second] * second_scale

        if self.deduction is not None:
            if isinstance(self.deduction, Percentage):
                d = points_possible * self.deduction.amount
            else:
                d = self.deduction.amount

            second_points = second_points - d

        points_marked = np.maximum(first_points, second_points)

        return gradebook.with_assignment(new_name, points_marked, points_possible)

    def _remove_parts(self, gradebook):
        for assignment_pair in self.selector.values():
            gradebook = gradebook.without_assignments(assignment_pair)
        return gradebook



