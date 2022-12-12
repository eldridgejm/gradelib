import pandas as pd
import numpy as np

from .core import Gradebook


def rank(scores) -> pd.Series:
    """The rank of each student according to score.

    Parameters
    ----------
    scores : pd.Series
        A series containing overall scores.

    Returns
    -------
    pd.Series
        A Series of the same size as `scores` containing the integer rank of
        each student in the class.

    """
    sorted_scores = scores.sort_values(ascending=False).to_frame()
    sorted_scores["rank"] = np.arange(1, len(sorted_scores) + 1)
    return sorted_scores["rank"]


def percentile(scores) -> pd.Series:
    """The percentile of each student according to score.

    Parameters
    ----------
    scores : pd.Series
        The scores used to compute the percentile.

    Returns
    -------
    pd.Series
        A Series of the same size as `scores` in which each entry is the
        student's percentile in the class, as a number between 0 and 1.

    """
    s = 1 - ((rank(scores) - 1) / len(rank(scores)))
    s.name = "percentile"
    return s


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


VALID_LETTERS = ("A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F")


def letter_grade_distribution(letters, valid_letters=VALID_LETTERS):
    """Counts the frequency of each letter grade.

    Parameters
    ----------
    letters : pd.Series
        The letter grades.

    valid_letters : Sequence[str]
        The possible letter grades.

    Returns
    -------
    pd.Series
        The count of each letter grade. The letters are guaranteed to be in
        order, from highest to lowest.

    """
    counts = letters.value_counts().reindex(valid_letters)
    counts.index.name = "Letter"
    counts.name = "Frequency"
    return counts.fillna(0).astype(int)


def lates(gradebook):
    """A table summarizing the number of late assignments."""
    late = gradebook.late.sum(axis=1).value_counts().to_frame()
    late.index.name = "Number of Lates"
    late.columns = ["Frequency"]
    return late.sort_index()


def outcomes(gradebook: Gradebook):
    """Compute a table summarizing student outcomes.

    Parameters
    ----------
    gradebook : Gradebook
        The gradebook used to compute outcomes.

    Returns
    -------
    pd.DataFrame
        A table with one row per student, and columns for grades in each
        assignment group, as well as overall score, letter grade, rank, and
        percentile. Sorted by score, from highest to lowest.

    """
    statistics = pd.DataFrame(
        {
            "overall score": gradebook.overall_score,
            "letter": gradebook.letter_grades,
            "rank": rank(gradebook.overall_score),
            "percentile": percentile(gradebook.overall_score),
        }
    )

    outcomes = pd.concat([gradebook.assignment_group_scores, statistics], axis=1)

    return outcomes.sort_values(by="overall score", ascending=False)
