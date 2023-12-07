import pandas as pd
import numpy as np

import gradelib
from gradelib import Percentage
from gradelib.policies.redemption import redeem

import pytest
from util import assert_gradebook_is_sound


# redeem -------------------------------------------------------------------------------


def test_on_single_assignment_pair():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    redeem(gradebook, {"mt01 with redemption": ("mt01", "mt01 - redemption")})

    # then
    assert gradebook.points_earned.loc["A1", "mt01 with redemption"] == 100
    assert gradebook.points_earned.loc["A2", "mt01 with redemption"] == 92
    assert "mt01" in gradebook.assignments
    assert "mt01 - redemption" in gradebook.assignments
    assert_gradebook_is_sound(gradebook)


def test_adds_note():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    redeem(gradebook, {"mt01 with redemption": ("mt01", "mt01 - redemption")})

    # then
    assert gradebook.notes == {
        "A1": {
            "redemption": [
                "Mt01 score: 95.00%. Mt01 - Redemption score: 100.00%. Mt01 - Redemption score used.",
            ]
        },
        "A2": {
            "redemption": [
                "Mt01 score: 92.00%. Mt01 - Redemption score: 60.00%. Mt01 score used.",
            ]
        },
    }


def test_on_multiple_assignment_pairs():
    # given
    columns = ["mt01", "mt01 - redemption", "mt02", "mt02 - redemption"]
    p1 = pd.Series(data=[95, 100, 45, 50], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60, 40, 35], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100, 50, 50], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    redeem(
        gradebook,
        {
            "mt01 with redemption": ("mt01", "mt01 - redemption"),
            "mt02 with redemption": ("mt02", "mt02 - redemption"),
        },
    )

    # then
    assert gradebook.points_earned.loc["A1", "mt01 with redemption"] == 100
    assert gradebook.points_earned.loc["A2", "mt01 with redemption"] == 92
    assert gradebook.points_earned.loc["A1", "mt02 with redemption"] == 50
    assert gradebook.points_earned.loc["A2", "mt02 with redemption"] == 40
    assert "mt01" in gradebook.assignments
    assert "mt01 - redemption" in gradebook.assignments
    assert "mt02" in gradebook.assignments
    assert "mt02 - redemption" in gradebook.assignments
    assert_gradebook_is_sound(gradebook)


def test_with_unequal_points_possible_scales_to_the_maximum_of_the_two():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 50], index=columns, name="A1")
    p2 = pd.Series(data=[92, 40], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 50], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    redeem(gradebook, {"mt01 with redemption": ("mt01", "mt01 - redemption")})

    # then
    assert gradebook.points_earned.loc["A1", "mt01 with redemption"] == 100
    assert gradebook.points_earned.loc["A2", "mt01 with redemption"] == 92
    assert gradebook.points_possible["mt01 with redemption"] == 100
    assert_gradebook_is_sound(gradebook)


def test_percentage_deduction_is_applied_to_points_earned():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 90], index=columns, name="A1")
    p2 = pd.Series(data=[50, 90], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    redeem(
        gradebook,
        {"mt01 with redemption": ("mt01", "mt01 - redemption")},
        deduction=Percentage(0.1),
    )

    # then
    assert gradebook.points_earned.loc["A1", "mt01 with redemption"] == 95
    assert gradebook.points_earned.loc["A2", "mt01 with redemption"] == 81
    assert "mt01" in gradebook.assignments
    assert "mt01 - redemption" in gradebook.assignments
    assert_gradebook_is_sound(gradebook)


def test_with_callable_deduction():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[50, 100], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    def deduction(gradebook, assignment_pair, student):
        if student == "A1":
            return gradelib.Points(50)
        else:
            return gradelib.Points(10)

    # when
    redeem(
        gradebook,
        {"mt01 with redemption": ("mt01", "mt01 - redemption")},
        deduction=deduction,
    )

    # then
    # after deduction, the redemption is no longer better
    assert gradebook.points_earned.loc["A1", "mt01 with redemption"] == 95
    assert gradebook.points_earned.loc["A2", "mt01 with redemption"] == 90
    assert "mt01" in gradebook.assignments
    assert "mt01 - redemption" in gradebook.assignments
    assert_gradebook_is_sound(gradebook)


def test_with_nans():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[np.nan, 100], index=columns, name="A1")
    p2 = pd.Series(data=[50, np.nan], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    redeem(gradebook, {"mt01 with redemption": ("mt01", "mt01 - redemption")})

    # then
    assert gradebook.points_earned.loc["A1", "mt01 with redemption"] == 100
    assert gradebook.points_earned.loc["A2", "mt01 with redemption"] == 50
    assert_gradebook_is_sound(gradebook)
