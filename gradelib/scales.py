"""Mapping point totals to letter grades."""

import collections

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


#: the default, standard grading scale
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


def _check_that_scale_monotonically_decreases(scale):
    prev = float("inf")
    for threshold in scale.values():
        if threshold >= prev:
            raise ValueError("Scale is not monotonically decreasing.")
        prev = threshold


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


def average_gpa(letter_grades, include_failing=False):
    """Compute the average GPA.

    Parameters
    ----------
    letter_grades
        A Series containing the letter grades.
    include_failing : Bool
        Whether or not to include failing grades in the calculation. 
        Default: False.

    Returns
    -------
    float
        The average GPA.
    
    """
    if not include_failing:
        letter_grades = letter_grades[letter_grades != "F"]

    letter_grade_values = pd.Series(
        {
            "A+": 4,
            "A": 4,
            "A-": 3.7,
            "B+": 3.3,
            "B": 3,
            "B-": 2.7,
            "C+": 2.3,
            "C": 2,
            "C-": 1.7,
            "D": 1,
            "F": 0,
        }
    )

    counts = letter_grades.value_counts()
    return (counts * letter_grade_values).sum() / counts.sum()


def letter_grade_distribution(letters):
    """Counts the frequency of each letter grade.

    Parameters
    ----------
    letters : pd.Series
        The letter grades.
    
    Returns
    -------
    pd.Series
        The count of each letter grade. The letters are guaranteed to be in
        order, from highest to lowest.

    """
    counts = letters.value_counts().reindex(DEFAULT_SCALE.keys())
    return counts.fillna(0).astype(int)


def plot_grade_distribution(
    scores, scale=None, x_min=0.6, x_max=1.02, bins="auto",
):
    """Visualize the grade distribution with respect to a scale.

    This will plot a histogram of the grade distribution, with each individual
    grade marked as a dot. Furthermore, if a gradine scale is provided,
    the letter grade thresholds are marked on the histogram as vertical lines,
    and the frequency of each letter grade is shown.

    Parameters
    ----------
    scores : pd.Series
        A series of scores between 0 and 1, with one score per student.
    scale : OrderedDict
        An ordered dictionary specifying the cutoffs for each letter grade.
        Optional. If `None` is passed, :attr:`DEFAULT_SCALE` is used. If 
        `False` is passed, no scale will be displayed. Default: `None`.
    x_min : float
        The smallest extent of the axis containing scores. Default: 0.6
    x_max : float
        The greatest extent of the axis containing scores. Default: 1.02
    bins
        What to pass as the `bins` argument to `np.hist`. Default: "auto"

    """
    if scale is None:
        scale = DEFAULT_SCALE

    # discard scores below the minimum
    scores = scores[scores >= x_min]

    scores = scores.sort_values()
    h = plt.hist(scores, bins=bins, density=True, color="blue", alpha=0.5)
    plt.scatter(
        scores, np.zeros_like(scores) - 0.1, marker="o", color="red", s=20, zorder=10
    )

    if scale:
        letters = map_scores_to_letter_grades(scores, scale)
        counts = letter_grade_distribution(letters)
        for letter, threshold in scale.items():
            if threshold > x_min:
                plt.axvline(threshold, color="black", linestyle=":")
                plt.text(threshold + 0.002, -0.6, f"{letter} ({counts[letter]})")

    plt.xlim([x_min, x_max])
    plt.ylim([-1, h[0].max() * 1.1])

    ax = plt.gca()
    ax.set_yticks([])


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
