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


# preprocessing
# ======================================================================================

# CombineAssignments
# --------------------------------------------------------------------------------------


def _combine_and_convert_deductions(parts, new_name, deductions, points_possible):
    """Concatenates all deductions from the given parts.

    Converts percentage deductions to points deductions along the way.

    Used in _combine_assignment

    """

    # combine and convert deductions
    def _convert_deduction(assignment, deduction):
        if isinstance(deduction, Percentage):
            possible = points_possible.loc[assignment]
            return Points(possible * deduction.amount)
        else:
            return deduction

    new_deductions = {}
    for student, assignments_dct in deductions.items():
        new_deductions[student] = {}

        combined_deductions = []
        for assignment, deductions_lst in assignments_dct.items():
            deductions_lst = [_convert_deduction(assignment, d) for d in deductions_lst]
            if assignment in parts:
                combined_deductions.extend(deductions_lst)
            else:
                new_deductions[student][assignment] = deductions_lst

        new_deductions[student][new_name] = combined_deductions

    return new_deductions


def _combine_assignment(gradebook, new_name, parts):
    """A helper function to combine assignments under the new name."""
    parts = list(parts)
    if gradebook.dropped[parts].any(axis=None):
        raise ValueError("Cannot combine assignments with drops.")

    assignment_points = gradebook.points_marked[parts].sum(axis=1)
    assignment_max = gradebook.points_possible[parts].sum()
    assignment_lateness = gradebook.lateness[parts].max(axis=1)

    new_points = gradebook.points_marked.copy().drop(columns=parts)
    new_max = gradebook.points_possible.copy().drop(parts)
    new_lateness = gradebook.lateness.copy().drop(columns=parts)

    new_points[new_name] = assignment_points
    new_max[new_name] = assignment_max
    new_lateness[new_name] = assignment_lateness

    # combines deductions from all of the parts, converting Percentage
    # to Points along the way.
    new_deductions = _combine_and_convert_deductions(
        parts, new_name, gradebook.deductions, gradebook.points_possible
    )

    # we're assuming that dropped was not set; we need to provide an empy
    # mask here, else ._replace will use the existing larger dropped table
    # of gradebook, which contains all parts
    new_dropped = _empty_mask_like(new_points)

    return gradebook._replace(
        points_marked=new_points,
        points_possible=new_max,
        dropped=new_dropped,
        lateness=new_lateness,
        deductions=new_deductions,
    )


class CombineAssignments:
    """Combine the assignment parts into one single assignment with the new name.

    Sometimes assignments may have several parts which are recorded separately
    in the grading software. For instance, a homework might
    have a written part and a programming part. This method makes it easy
    to combine these parts into a single assignment.

    The individual assignment parts are removed from the gradebook.

    The new marked points and possible points are calculated by addition.
    The lateness of the new assignment is the *maximum* lateness of any of
    its parts.

    Deductions are concatenated. Points are propagated unchanged, but
    Percentage objects are converted to Points according to the ratio of
    the part's value to the total points possible. For example, if the
    first part is worth 70 points, and the second part is worth 30 points,
    and a 25% Percentage is applied to the second part, it is converted to
    a 25% * 30 = 7.5 point Points.

    It is unclear what the result should be if any of the assignments to be
    unified has been dropped, but other parts have not. For this reason,
    this method will raise a `ValueError` if *any* of the parts have been
    dropped.

    Parameters
    ----------
    dct_or_callable : Mapping[str, Collection[str]]
        Either: 1) a mapping whose keys are new assignment names, and whose
        values are collections of assignments that should be unified under
        their common key; or 2) a callable which maps assignment names to
        new assignment by which they should be grouped.

    Raises
    ------
    ValueError
        If any of the assignments to be unified is marked as dropped. See above for
        rationale.

    Example
    -------

    Assuming the gradebook has assignments named `homework 01`, `homework 01 - programming`,
    `homework 02`, `homework 02 - programming`, etc., the following will "combine" the
    assignments into `homework 01`, `homework 02`, etc:

        >>> gradebook.apply(CombineAssignments(lambda s: s.split('-')[0].strip()))

    Alternatively, you could write:

        >>> gradebook.apply(CombineAssignments({
            'homework 01': {'homework 01', 'homework 01 - programming'},
            'homework 02': {'homework 02', 'homework 02 - programming'}
            }))

    """

    def __init__(self, dct_or_callable):
        self.dct_or_callable = dct_or_callable

    def __call__(self, gradebook):
        pass

        if not callable(self.dct_or_callable):
            dct = self.dct_or_callable
        else:
            to_key = self.dct_or_callable
            dct = {}
            for assignment in gradebook.assignments:
                key = to_key(assignment)
                if key not in dct:
                    dct[key] = []
                dct[key].append(assignment)

        result = gradebook
        for key, value in dct.items():
            result = _combine_assignment(result, key, value)

        return result


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

class Redemption:

    def __init__(self, assignment_pairs, remove_parts=False, deduction=None):
        self.assignment_pairs = assignment_pairs
        self.remove_parts = remove_parts
        self.deduction = deduction

    def __call__(self, gradebook):
        for new_name, assignment_pair in self.assignment_pairs.items():
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
        for assignment_pair in self.assignment_pairs.values():
            gradebook = gradebook.without_assignments(assignment_pair)
        return gradebook



