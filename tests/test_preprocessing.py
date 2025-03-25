import pandas as pd
import numpy as np

import gradelib
from gradelib import preprocessing

import pytest  # pyright: ignore


# combine_assignment_parts -------------------------------------------------------------


def test_combine_assignment_parts():
    """test that points_earned / points_possible are added across unified assignments"""
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    # when
    preprocessing.combine_assignment_parts(gradebook, {"hw01": HOMEWORK_01_PARTS})

    # then
    assert len(gradebook.assignments) == 3
    assert gradebook.points_possible["hw01"] == 52
    assert gradebook.points_earned.loc["A1", "hw01"] == 31

    assert gradebook.points_possible.shape[0] == 3
    assert gradebook.late.shape[1] == 3
    assert gradebook.dropped.shape[1] == 3
    assert gradebook.points_earned.shape[1] == 3


def test_combine_assignment_parts_with_multiple_in_dictionary():
    """test that points_earned / points_possible are added across unified assignments"""
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "hw02 - testing"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")
    HOMEWORK_02_PARTS = gradebook.assignments.starting_with("hw02")

    # when
    preprocessing.combine_assignment_parts(
        gradebook, {"hw01": HOMEWORK_01_PARTS, "hw02": HOMEWORK_02_PARTS}
    )

    # then
    assert len(gradebook.assignments) == 2

    assert gradebook.points_possible["hw01"] == 52
    assert gradebook.points_earned.loc["A1", "hw01"] == 31

    assert gradebook.points_possible["hw02"] == 120
    assert gradebook.points_earned.loc["A1", "hw02"] == 110

    assert gradebook.points_possible.shape[0] == 2
    assert gradebook.late.shape[1] == 2
    assert gradebook.dropped.shape[1] == 2
    assert gradebook.points_earned.shape[1] == 2


def test_combine_assignment_parts_with_prefixes():
    """test that points_earned / points_possible are added across unified assignments"""
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "hw02 - testing", "lab 01"]
    p1 = pd.Series(data=[1, 30, 90, 20, 10], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20, 10], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20, 10], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # when
    preprocessing.combine_assignment_parts(
        gradebook,
        gradebook.assignments.starting_with("hw").group_by(lambda s: s.split(" - ")[0]),
    )

    # then
    assert len(gradebook.assignments) == 3

    assert gradebook.points_possible["hw01"] == 52
    assert gradebook.points_earned.loc["A1", "hw01"] == 31

    assert gradebook.points_possible["hw02"] == 120
    assert gradebook.points_earned.loc["A1", "hw02"] == 110

    assert gradebook.points_possible.shape[0] == 3
    assert gradebook.late.shape[1] == 3
    assert gradebook.dropped.shape[1] == 3
    assert gradebook.points_earned.shape[1] == 3


def test_combine_assignment_parts_uses_max_lateness_for_assignment_pieces():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    gradebook.lateness.loc["A1", "hw01"] = pd.Timedelta(days=3)
    gradebook.lateness.loc["A1", "hw01 - programming"] = pd.Timedelta(days=5)
    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    # when
    preprocessing.combine_assignment_parts(gradebook, {"hw01": HOMEWORK_01_PARTS})

    # then
    assert gradebook.lateness.loc["A1", "hw01"] == pd.Timedelta(days=5)


def test_combine_assignment_parts_raises_if_any_part_is_dropped():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    gradebook.dropped.loc["A1", "hw01"] = True
    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    with pytest.raises(ValueError):
        preprocessing.combine_assignment_parts(gradebook, {"hw01": HOMEWORK_01_PARTS})


def test_combine_assignment_parts_copies_attributes():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    preprocessing.combine_assignment_parts(gradebook, {"hw01": HOMEWORK_01_PARTS})


def test_combine_assignment_parts_resets_groups():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)
    gradebook.grading_groups = {
        "homeworks": gradelib.GradingGroup(
            {"hw01": 0.25, "hw01 - programming": 0.25, "hw02": 0.5}, 0.5
        ),
        "labs": gradelib.GradingGroup({"lab01": 1}, 0.5),
    }

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    # when
    preprocessing.combine_assignment_parts(gradebook, {"hw01": HOMEWORK_01_PARTS})

    # then
    assert gradebook.grading_groups == {}


# combine_assignment_versions ----------------------------------------------------------


def test_combine_assignment_versions_removes_assignment_versions():
    # given
    columns = ["mt - version a", "mt - version b"]
    p1 = pd.Series(data=[50, np.nan], index=columns, name="A1")
    p2 = pd.Series(data=[np.nan, 30], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 50], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # when
    preprocessing.combine_assignment_versions(gradebook, {"midterm": columns})

    # then
    assert list(gradebook.assignments) == ["midterm"]


def test_combine_assignment_versions_merges_points():
    # given
    columns = ["mt - version a", "mt - version b", "mt - version c"]
    p1 = pd.Series(data=[50, np.nan, np.nan], index=columns, name="A1")
    p2 = pd.Series(data=[np.nan, 30, np.nan], index=columns, name="A2")
    p3 = pd.Series(data=[np.nan, np.nan, 40], index=columns, name="A3")
    points_earned = pd.DataFrame([p1, p2, p3])
    points_possible = pd.Series([50, 50, 40], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # when
    preprocessing.combine_assignment_versions(gradebook, {"midterm": columns})

    # then
    assert gradebook.points_earned.loc["A1", "midterm"] == 50
    assert gradebook.points_earned.loc["A2", "midterm"] == 30
    assert gradebook.points_earned.loc["A3", "midterm"] == 40


def test_combine_assignment_versions_raises_if_any_dropped():
    # given
    columns = ["mt - version a", "mt - version b", "mt - version c"]
    p1 = pd.Series(data=[50, np.nan, np.nan], index=columns, name="A1")
    p2 = pd.Series(data=[np.nan, 30, np.nan], index=columns, name="A2")
    p3 = pd.Series(data=[np.nan, np.nan, 40], index=columns, name="A3")
    points_earned = pd.DataFrame([p1, p2, p3])
    points_possible = pd.Series([50, 50, 40], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    gradebook.dropped.loc["A1", "mt - version a"] = True

    # when
    with pytest.raises(ValueError):
        preprocessing.combine_assignment_versions(gradebook, {"midterm": columns})


def test_combine_assignment_versions_raises_if_points_earned_in_multiple_versions():
    # given
    columns = ["mt - version a", "mt - version b", "mt - version c", "homework"]
    p1 = pd.Series(data=[50, 20, np.nan, 10], index=columns, name="A1")
    p2 = pd.Series(data=[np.nan, 30, np.nan, 10], index=columns, name="A2")
    p3 = pd.Series(data=[np.nan, np.nan, 40, 10], index=columns, name="A3")
    points_earned = pd.DataFrame([p1, p2, p3])
    points_possible = pd.Series([50, 50, 40, 10], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # when
    with pytest.raises(ValueError):
        preprocessing.combine_assignment_versions(gradebook, {"midterm": columns})


def test_combine_assignment_versions_doesnt_raise_if_only_one_assignment_version_turned_int():
    # given
    columns = ["mt - version a", "mt - version b", "mt - version c", "homework"]
    p1 = pd.Series(data=[50, np.nan, np.nan, 10], index=columns, name="A1")
    p2 = pd.Series(data=[np.nan, 30, np.nan, 10], index=columns, name="A2")
    p3 = pd.Series(data=[np.nan, np.nan, 40, 10], index=columns, name="A3")
    points_earned = pd.DataFrame([p1, p2, p3])
    points_possible = pd.Series([50, 50, 50, 10], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # when
    PARTS = gradebook.assignments.starting_with("mt")
    preprocessing.combine_assignment_versions(gradebook, {"midterm": PARTS})

    # then
    assert gradebook.points_earned.loc["A1", "midterm"] == 50


def test_combine_assignment_versions_uses_lateness_of_turned_in_version():
    # given
    columns = ["mt - version a", "mt - version b", "mt - version c"]
    p1 = pd.Series(data=[50, np.nan, np.nan], index=columns, name="A1")
    p2 = pd.Series(data=[np.nan, 30, np.nan], index=columns, name="A2")
    p3 = pd.Series(data=[np.nan, np.nan, 40], index=columns, name="A3")
    points_earned = pd.DataFrame([p1, p2, p3])
    points_possible = pd.Series([50, 50, 40], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    gradebook.lateness.loc["A1", "mt - version a"] = pd.Timedelta(days=3)
    gradebook.lateness.loc["A2", "mt - version b"] = pd.Timedelta(days=2)

    # when
    preprocessing.combine_assignment_versions(gradebook, {"mt": columns})

    # then
    assert gradebook.lateness.loc["A1", "mt"] == pd.Timedelta(days=3)
    assert gradebook.lateness.loc["A2", "mt"] == pd.Timedelta(days=2)
