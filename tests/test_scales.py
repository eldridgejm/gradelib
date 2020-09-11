import gradelib

import pandas as pd


def test_map_score_to_letter_grade_on_example():
    # given
    scores = pd.Series(data=[0.84, 0.95, 0.55])

    # when
    letters = gradelib.map_scores_to_letter_grades(scores)

    # then
    letters.iloc[0] = "B"
    letters.iloc[1] = "A"
    letters.iloc[2] = "F"


def test_average_gpa():
    # given
    letters = pd.Series(data=["A", "B", "B-", "C"])

    # when
    gpa = gradelib.average_gpa(letters)

    # then
    assert gpa == (4 + 3 + 2.7 + 2) / 4


def test_average_gpa_without_failing_grades():
    # given
    letters = pd.Series(data=["A", "B", "B-", "C", "F"])

    # when
    gpa_1 = gradelib.average_gpa(letters)
    gpa_2 = gradelib.average_gpa(letters, include_failing=True)

    # then
    assert gpa_1 == (4 + 3 + 2.7 + 2) / 4
    assert gpa_2 == (4 + 3 + 2.7 + 2) / 5


def test_distribution():
    # given
    letters = pd.Series(data=["A", "B", "A", "A", "B+", "C", "C-", "F", "B"])

    # when
    distribution = gradelib.letter_grade_distribution(letters)

    # then
    expected = pd.Series(
        {
            "A+": 0,
            "A": 3,
            "A-": 0,
            "B+": 1,
            "B": 2,
            "B-": 0,
            "C+": 0,
            "C": 1,
            "C-": 1,
            "D": 0,
            "F": 1,
        }
    )

    assert (distribution == expected).all()
