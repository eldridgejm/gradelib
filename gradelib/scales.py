"""Mapping point totals to letter grades."""

import collections

import pandas as pd
import numpy as np


# helper functions =====================================================================


def _check_that_scale_monotonically_decreases(scale):
    prev = float("inf")
    for threshold in scale.values():
        if threshold >= prev:
            raise ValueError("Scale is not monotonically decreasing.")
        prev = threshold


# common scales ========================================================================

DEFAULT_SCALE = collections.OrderedDict(
    [
        ("A+", 0.97),
        ("A", 0.93),
        ("A-", 0.90),
        ("B+", 0.87),
        ("B", 0.83),
        ("B-", 0.80),
        ("C+", 0.77),
        ("C", 0.73),
        ("C-", 0.70),
        ("D", 0.60),
        ("F", 0),
    ]
)
"""The default grading scale."""

#: a rounded version of the default scale, where each threshold is one half point lower
ROUNDED_DEFAULT_SCALE = DEFAULT_SCALE.copy()
for _k, _v in ROUNDED_DEFAULT_SCALE.items():
    ROUNDED_DEFAULT_SCALE[_k] = _v - 0.005
ROUNDED_DEFAULT_SCALE["F"] = 0
"""The default grading scale in which scores are rounded up. E.g., a 92.5% is an A."""


# public functions =====================================================================


def map_scores_to_letter_grades(scores, scale=None):
    """Map each raw score to a letter grade.

    Parameters
    ----------
    scores : pandas.Series
        A series contains scores as floats between 0 and 1.
    scale : OrderedDict
        An ordered dictionary mapping letter grades to their thresholds.
        Default: :attr:`DEFAULT_SCALE`.

    Returns
    -------
    pandas.Series
        A series containing the resulting letter grades.

    Raises
    ------
    ValueError
        If the provided scale has invalid letter grades.

    """
    if scale is None:
        scale = DEFAULT_SCALE
    else:
        if list(scale) != list(DEFAULT_SCALE):
            raise ValueError(
                f"Scale has invalid letter grades. Must be in {set(DEFAULT_SCALE.keys())}"
            )
        _check_that_scale_monotonically_decreases(scale)

    def _map(score):
        for letter, threshold in scale.items():
            if score >= threshold:
                return letter
        else:
            return "F"

    return scores.apply(_map)


def find_robust_scale(scores, scale=None, grade_gap=0.005, threshold_gap=0.01):
    """Find a robust grading scale.

    Given an initial grading scale, finds the largest value of each threshold
    which is at least `grade_gap` larger than the highest grade below the
    threshold.

    In other words, lowers the threshold for each letter grade until no student
    is agonizingly close to a higher letter grade.

    Parameters
    ----------
    scores : pd.Series
        A series containing the total scores for each student.
    scale
        An initial grading scale to relax and make robust.
        Default: :attr:`DEFAULT_SCALE`
    grade_gap : float
        The minimum difference between a threshold and the highest grade below
        the threshold.
    threshold_gap : float
        The minimum difference between consecutive thresholds.

    Returns
    -------
    OrderedDict
        The robust grading scale.

    """
    if scale is None:
        scale = DEFAULT_SCALE

    scale_dummy_scores = np.array(list(scale.values()))
    scores = np.append(scores, scale_dummy_scores)

    scores = np.sort(scores)
    deltas = np.diff(scores)

    ix = deltas > grade_gap
    possible_thresholds = scores[1:][ix]

    robust_scale = collections.OrderedDict()
    prev_threshold = float("inf")
    for letter, threshold in scale.items():
        threshold = min(threshold, prev_threshold - threshold_gap)
        z = robust_scale[letter] = np.amax(
            possible_thresholds[possible_thresholds <= threshold], initial=0
        )
        prev_threshold = z

    return robust_scale
