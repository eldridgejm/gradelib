import pandas as pd
import numpy as np

import gradelib
from gradelib import Percentage

import pytest
from util import assert_gradebook_is_sound




# Redeem -------------------------------------------------------------------------------


def test_redemption_on_single_assignment_pair():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    actual = gradebook.apply(
        gradelib.policies.Redeem(
            {"mt01 with redemption": ("mt01", "mt01 - redemption")}
        )
    )

    # then
    assert actual.points_earned.loc["A1", "mt01 with redemption"] == 100
    assert actual.points_earned.loc["A2", "mt01 with redemption"] == 92
    assert "mt01" in actual.assignments
    assert "mt01 - redemption" in actual.assignments
    assert_gradebook_is_sound(actual)


def test_redemption_adds_note():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    actual = gradebook.apply(
        gradelib.policies.Redeem(
            {"mt01 with redemption": ("mt01", "mt01 - redemption")}
        )
    )

    # then
    assert actual.notes == {
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


def test_redemption_on_multiple_assignment_pairs():
    # given
    columns = ["mt01", "mt01 - redemption", "mt02", "mt02 - redemption"]
    p1 = pd.Series(data=[95, 100, 45, 50], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60, 40, 35], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100, 50, 50], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    actual = gradebook.apply(
        gradelib.policies.Redeem(
            {
                "mt01 with redemption": ("mt01", "mt01 - redemption"),
                "mt02 with redemption": ("mt02", "mt02 - redemption"),
            }
        )
    )

    # then
    assert actual.points_earned.loc["A1", "mt01 with redemption"] == 100
    assert actual.points_earned.loc["A2", "mt01 with redemption"] == 92
    assert actual.points_earned.loc["A1", "mt02 with redemption"] == 50
    assert actual.points_earned.loc["A2", "mt02 with redemption"] == 40
    assert "mt01" in actual.assignments
    assert "mt01 - redemption" in actual.assignments
    assert "mt02" in actual.assignments
    assert "mt02 - redemption" in actual.assignments
    assert_gradebook_is_sound(actual)


def test_redemption_with_prefix_selector():
    # given
    columns = ["mt01", "mt01 - redemption", "mt02", "mt02 - redemption"]
    p1 = pd.Series(data=[95, 100, 45, 50], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60, 40, 35], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100, 50, 50], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    actual = gradebook.apply(gradelib.policies.Redeem(["mt01", "mt02"]))

    # then
    assert actual.points_earned.loc["A1", "mt01 with redemption"] == 100
    assert actual.points_earned.loc["A2", "mt01 with redemption"] == 92
    assert actual.points_earned.loc["A1", "mt02 with redemption"] == 50
    assert actual.points_earned.loc["A2", "mt02 with redemption"] == 40
    assert "mt01" in actual.assignments
    assert "mt01 - redemption" in actual.assignments
    assert "mt02" in actual.assignments
    assert "mt02 - redemption" in actual.assignments
    assert_gradebook_is_sound(actual)


def test_redemption_with_remove_parts():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    actual = gradebook.apply(
        gradelib.policies.Redeem(
            {"mt01 with redemption": ("mt01", "mt01 - redemption")}, remove_parts=True
        )
    )

    # then
    assert actual.points_earned.loc["A1", "mt01 with redemption"] == 100
    assert actual.points_earned.loc["A2", "mt01 with redemption"] == 92
    assert "mt01" not in actual.assignments
    assert "mt01 - redemption" not in actual.assignments
    assert_gradebook_is_sound(actual)


def test_redemption_with_dropped_assignment_parts_raises():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    gradebook.dropped.loc["A1", "mt01"] = True

    # when
    with pytest.raises(ValueError):
        actual = gradebook.apply(
            gradelib.policies.Redeem(
                {"mt01 with redemption": ("mt01", "mt01 - redemption")}
            )
        )


def test_redemption_with_unequal_points_possible_scales_to_the_maximum_of_the_two():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 50], index=columns, name="A1")
    p2 = pd.Series(data=[92, 40], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 50], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    actual = gradebook.apply(
        gradelib.policies.Redeem(
            {"mt01 with redemption": ("mt01", "mt01 - redemption")}
        )
    )

    # then
    assert actual.points_earned.loc["A1", "mt01 with redemption"] == 100
    assert actual.points_earned.loc["A2", "mt01 with redemption"] == 92
    assert actual.points_possible["mt01 with redemption"] == 100
    assert_gradebook_is_sound(actual)


def test_redemption_with_deduction():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[50, 100], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    actual = gradebook.apply(
        gradelib.policies.Redeem(
            {"mt01 with redemption": ("mt01", "mt01 - redemption")},
            deduction=Percentage(0.25),
        )
    )

    # then
    assert actual.points_earned.loc["A1", "mt01 with redemption"] == 95
    assert actual.points_earned.loc["A2", "mt01 with redemption"] == 75
    assert "mt01" in actual.assignments
    assert "mt01 - redemption" in actual.assignments
    assert_gradebook_is_sound(actual)


def test_redemption_with_nans():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[np.nan, 100], index=columns, name="A1")
    p2 = pd.Series(data=[50, np.nan], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    actual = gradelib.policies.Redeem(
        {"mt01 with redemption": ("mt01", "mt01 - redemption")}
    )(gradebook)

    # then
    assert actual.points_earned.loc["A1", "mt01 with redemption"] == 100
    assert actual.points_earned.loc["A2", "mt01 with redemption"] == 50
    assert_gradebook_is_sound(actual)
