import math

import pandas as pd

import gradelib


def test_average_gpa():
    # given
    letters = pd.Series(data=["A", "B", "B-", "C"])

    # when
    gpa = gradelib.statistics.average_gpa(letters)

    # then
    assert gpa == (4 + 3 + 2.7 + 2) / 4


def test_average_gpa_without_failing_grades():
    # given
    letters = pd.Series(data=["A", "B", "B-", "C", "F"])

    # when
    gpa_1 = gradelib.statistics.average_gpa(letters)
    gpa_2 = gradelib.statistics.average_gpa(letters, include_failing=True)

    # then
    assert gpa_1 == (4 + 3 + 2.7 + 2) / 4
    assert gpa_2 == (4 + 3 + 2.7 + 2) / 5


def test_distribution():
    # given
    letters = pd.Series(data=["A", "B", "A", "A", "B+", "C", "C-", "F", "B"])

    # when
    distribution = gradelib.statistics.letter_grade_distribution(letters)

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


def test_rank():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    p3 = pd.Series(data=[2, 50, 100, 20], index=columns, name="A3")
    points = pd.DataFrame([p1, p2, p3])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    homeworks = gradebook.assignments.starting_with("hw")

    gradebook.grading_groups = {"homeworks": (homeworks, 0.75), "lab01": 0.25}

    # if we are dropping 1 HW, the right strategy is to drop the 50 point HW
    # for A1 and to drop the 100 point homework for A2

    # when
    ranks = gradelib.statistics.rank(gradebook.overall_score)

    # then
    assert ranks.loc["A1"] == 2
    assert ranks.loc["A2"] == 3
    assert ranks.loc["A3"] == 1


def test_percentile():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    p3 = pd.Series(data=[2, 50, 100, 20], index=columns, name="A3")
    points = pd.DataFrame([p1, p2, p3])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    homeworks = gradebook.assignments.starting_with("hw")

    gradebook.grading_groups = {"homeworks": (homeworks, 0.75), "lab01": 0.25}

    # if we are dropping 1 HW, the right strategy is to drop the 50 point HW
    # for A1 and to drop the 100 point homework for A2

    # when
    percentiles = gradelib.statistics.percentile(gradebook.overall_score)

    # then
    assert math.isclose(percentiles.loc["A1"], 2 / 3)
    assert math.isclose(percentiles.loc["A2"], 1 / 3)
    assert math.isclose(percentiles.loc["A3"], 1)


def test_outcomes():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    p3 = pd.Series(data=[2, 50, 100, 20], index=columns, name="A3")
    points = pd.DataFrame([p1, p2, p3])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    homeworks = gradebook.assignments.starting_with("hw")

    gradebook.grading_groups = {"homeworks": (homeworks, 0.75), "lab01": 0.25}

    # if we are dropping 1 HW, the right strategy is to drop the 50 point HW
    # for A1 and to drop the 100 point homework for A2

    # when
    outcomes = gradelib.statistics.outcomes(gradebook)

    assert outcomes.iloc[0]["rank"] == 1
