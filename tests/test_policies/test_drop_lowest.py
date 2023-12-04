import pandas as pd

import gradelib

import pytest
from util import assert_gradebook_is_sound


def test_drop_lowest_with_callable_within():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    homeworks = gradebook.assignments.starting_with("hw")

    gradebook.grading_groups = {"homeworks": (homeworks, 0.75), "lab01": 0.25}

    # if we are dropping 1 HW, the right strategy is to drop the 50 point HW
    # for A1 and to drop the 100 point homework for A2

    # when
    gradelib.policies.drop_lowest(gradebook, 1, within=homeworks)

    # then
    assert gradebook.dropped.iloc[0, 1]
    assert gradebook.dropped.iloc[1, 2]
    assert list(gradebook.dropped.sum(axis=1)) == [1, 1]
    assert_gradebook_is_sound(gradebook)


def test_drop_lowest_maximizes_overall_score():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    HOMEWORKS = gradebook.assignments.starting_with("hw")
    gradebook.grading_groups = {"homeworks": (HOMEWORKS, 0.75), "lab01": 0.25}

    # if we are dropping 1 HW, the right strategy is to drop the 50 point HW
    # for A1 and to drop the 100 point homework for A2

    # when
    gradelib.policies.drop_lowest(gradebook, 1, within=HOMEWORKS)

    # then
    assert gradebook.dropped.iloc[0, 1]
    assert gradebook.dropped.iloc[1, 2]
    assert list(gradebook.dropped.sum(axis=1)) == [1, 1]
    assert_gradebook_is_sound(gradebook)


def test_drop_lowest_with_multiple_dropped():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    homeworks = gradebook.assignments.starting_with("hw")

    gradebook.grading_groups = {"homeworks": (homeworks, 0.75), "lab01": 0.25}

    # if we are dropping 1 HW, the right strategy is to drop the 50 point HW
    # for A1 and to drop the 100 point homework for A2

    # when
    gradelib.policies.drop_lowest(gradebook, 2, within=homeworks)

    # then
    assert not gradebook.dropped.iloc[0, 2]
    assert not gradebook.dropped.iloc[1, 0]
    assert list(gradebook.dropped.sum(axis=1)) == [2, 2]
    assert_gradebook_is_sound(gradebook)


def test_drop_lowest_ignores_assignments_already_dropped():
    # given
    columns = ["hw01", "hw02", "hw03", "hw04"]
    p1 = pd.Series(data=[9, 0, 7, 0], index=columns, name="A1")
    p2 = pd.Series(data=[10, 10, 10, 10], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([10, 10, 10, 10], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A1", "hw04"] = True

    gradebook.grading_groups = {
        "homeworks": (gradebook.assignments.starting_with("hw"), 1),
    }

    # since A1's perfect homeworks are already dropped, we should drop a third
    # homework, too: this will be HW03

    # when
    gradelib.policies.drop_lowest(gradebook, 1)

    # then
    assert gradebook.dropped.loc["A1", "hw04"]
    assert gradebook.dropped.loc["A1", "hw02"]
    assert gradebook.dropped.loc["A1", "hw03"]
    assert list(gradebook.dropped.sum(axis=1)) == [3, 1]
    assert_gradebook_is_sound(gradebook)


def test_drop_lowest_with_multiple_dropped_adds_note():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    homeworks = gradebook.assignments.starting_with("hw")

    gradebook.grading_groups = {"homeworks": (homeworks, 0.75), "lab01": 0.25}

    # if we are dropping 1 HW, the right strategy is to drop the 50 point HW
    # for A1 and to drop the 100 point homework for A2

    # when
    gradelib.policies.drop_lowest(gradebook, 2, within=homeworks)

    assert gradebook.notes == {
        "A1": {"drops": ["Hw01 dropped.", "Hw02 dropped."]},
        "A2": {"drops": ["Hw02 dropped.", "Hw03 dropped."]},
    }
