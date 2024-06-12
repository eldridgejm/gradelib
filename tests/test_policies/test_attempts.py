import pandas as pd
import numpy as np

import gradelib
from gradelib.policies.attempts import take_best

from util import assert_gradebook_is_sound


def test_returns_maximum():
    # given
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    take_best(gradebook, {"mt01 with retry": ["mt01", "mt01 - retry"]})

    # then
    assert gradebook.points_earned.loc["A1", "mt01 with retry"] == 100 / 100
    assert gradebook.points_earned.loc["A2", "mt01 with retry"] == 92 / 100
    assert_gradebook_is_sound(gradebook)


def test_removes_attempts_by_default():
    # given
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    take_best(gradebook, {"mt01 with retry": ["mt01", "mt01 - retry"]})

    # then
    assert "mt01" not in gradebook.points_earned.columns
    assert "mt01 - retry" not in gradebook.points_earned.columns


def test_keeps_attempts_if_requested():
    # given
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    take_best(gradebook, {"mt01 with retry": ["mt01", "mt01 - retry"]}, remove=False)

    # then
    assert "mt01" in gradebook.points_earned.columns
    assert "mt01 - retry" in gradebook.points_earned.columns


def test_adds_note():
    # given
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    take_best(gradebook, {"mt01 with retry": ["mt01", "mt01 - retry"]})

    # then
    assert gradebook.notes == {
        "A1": {
            "attempts": [
                "Mt01 score: 95.00%. Mt01 - Retry score: 100.00%. Mt01 - Retry score (100.00%) used.",
            ]
        },
        "A2": {
            "attempts": [
                "Mt01 score: 92.00%. Mt01 - Retry score: 60.00%. Mt01 score (92.00%) used.",
            ]
        },
    }


def test_does_not_print_warning_if_all_attempts_are_nan(recwarn):
    """If all of a student's attempts are nan, no warning should be printed."""
    # given
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[np.nan, np.nan], index=columns, name="A1")
    points = pd.DataFrame([p1])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    # assert that no warnings are raised
    take_best(gradebook, {"mt01 with retry": ["mt01", "mt01 - retry"]})

    # then
    # no warnings should be raised
    assert len(recwarn) == 0


def test_best_attempt_is_nan_if_none_of_the_parts_are_attempted():
    """If all of a student's attempts are nan, the best attempt should be nan."""
    # given
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[np.nan, np.nan], index=columns, name="A1")
    points = pd.DataFrame([p1])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    take_best(gradebook, {"mt01 with retry": ["mt01", "mt01 - retry"]})

    # then
    assert pd.isna(gradebook.points_earned.loc["A1", "mt01 with retry"])
    assert_gradebook_is_sound(gradebook)


def test_ignores_nan_when_taking_maximum():
    """Nans should be ignored. That is, if a student has a nan for one assignment, the
    maximum should be taken from the other assignments."""
    # given
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[np.nan, 90], index=columns, name="A1")
    p2 = pd.Series(data=[50, np.nan], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    take_best(gradebook, {"mt01 with retry": ["mt01", "mt01 - retry"]})

    # then
    assert gradebook.points_earned.loc["A1", "mt01 with retry"] == 0.9
    assert gradebook.points_earned.loc["A2", "mt01 with retry"] == 0.5
    assert_gradebook_is_sound(gradebook)


def test_points_possible():
    # given
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    take_best(
        gradebook,
        {"mt01 with retry": ["mt01", "mt01 - retry"]},
        points_possible=20,
    )

    # then
    assert np.isclose(gradebook.points_earned.loc["A1", "mt01 with retry"], 20)
    assert np.isclose(gradebook.points_earned.loc["A2", "mt01 with retry"], 18.4)


def test_with_penalty_policy():
    # given
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[60, 100], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    def cap_at_90(i, score):
        if i > 0:
            return min(score, 0.9)
        else:
            return score

    # when
    take_best(
        gradebook,
        {"mt01 with retry": ["mt01", "mt01 - retry"]},
        policy=cap_at_90,
    )

    # then
    assert np.isclose(gradebook.points_earned.loc["A1", "mt01 with retry"], 0.95)
    assert np.isclose(gradebook.points_earned.loc["A2", "mt01 with retry"], 0.9)


def test_with_penalty_policy_adds_notes():
    # given
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[60, 100], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    def cap_at_90(i, score):
        if i > 0:
            return min(score, 0.9)
        else:
            return score

    # when
    take_best(
        gradebook,
        {"mt01 with retry": ["mt01", "mt01 - retry"]},
        policy=cap_at_90,
    )

    # then
    assert gradebook.notes == {
        "A1": {
            "attempts": [
                "Mt01 score: 95.00%. Mt01 - Retry raw score: 100.00%, after penalty for retrying: 90.00%. Mt01 score (95.00%) used.",
            ]
        },
        "A2": {
            "attempts": [
                "Mt01 score: 60.00%. Mt01 - Retry raw score: 100.00%, after penalty for retrying: 90.00%. Mt01 - Retry score (90.00%) used.",
            ]
        },
    }
