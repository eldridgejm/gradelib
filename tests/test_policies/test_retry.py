import pandas as pd
import numpy as np

import gradelib
from gradelib.policies.retries import retry

from util import assert_gradebook_is_sound


# retry -------------------------------------------------------------------------------


def test_maximum():
    # given
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    retry(gradebook, {"mt01 with retry": ["mt01", "mt01 - retry"]})

    # then
    assert gradebook.points_earned.loc["A1", "mt01 with retry"] == 100 / 100
    assert gradebook.points_earned.loc["A2", "mt01 with retry"] == 92 / 100
    assert "mt01" in gradebook.assignments
    assert "mt01 with retry" in gradebook.assignments
    assert_gradebook_is_sound(gradebook)


def test_maximum_adds_note():
    # given
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    retry(gradebook, {"mt01 with retry": ["mt01", "mt01 - retry"]})

    # then
    assert gradebook.notes == {
        "A1": {
            "retries": [
                "Mt01 score: 95.00%. Mt01 - Retry score: 100.00%. Mt01 - Retry score used.",
            ]
        },
        "A2": {
            "retries": [
                "Mt01 score: 92.00%. Mt01 - Retry score: 60.00%. Mt01 score used.",
            ]
        },
    }


def test_with_nans():
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
    retry(gradebook, {"mt01 with retry": ["mt01", "mt01 - retry"]})

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
    retry(
        gradebook,
        {"mt01 with retry": ["mt01", "mt01 - retry"]},
        points_possible=20,
    )

    # then
    assert np.isclose(gradebook.points_earned.loc["A1", "mt01 with retry"], 20)
    assert np.isclose(gradebook.points_earned.loc["A2", "mt01 with retry"], 18.4)
