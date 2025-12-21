import numpy as np
import pandas as pd
from util import assert_gradebook_is_sound

import gradelib
from gradelib.policies.attempts import take_best


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
                "Mt01 score: 95.00%. Mt01 - Retry score: 100.00%. "
                "Mt01 - Retry score (100.00%) used.",
            ]
        },
        "A2": {
            "attempts": [
                "Mt01 score: 92.00%. Mt01 - Retry score: 60.00%. "
                "Mt01 score (92.00%) used.",
            ]
        },
    }


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
    columns = ["mt01", "mt01 - retry 01", "mt01 - retry 02"]
    p1 = pd.Series(data=[95, 100, 85], index=columns, name="A1")
    p2 = pd.Series(data=[60, 85, 100], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    def cap_at_90(original_scores):
        """A policy that caps all but the first attempt at 90%."""
        return pd.Series(
            np.concatenate(
                [
                    original_scores.values[:1],
                    np.minimum(original_scores.values[1:], 0.9),
                ]
            ),
            index=original_scores.index,
        )

    # when
    take_best(
        gradebook,
        {"mt01 with retry": ["mt01", "mt01 - retry 01", "mt01 - retry 02"]},
        penalty_strategy=cap_at_90,
    )

    # then
    assert np.isclose(gradebook.points_earned.loc["A1", "mt01 with retry"], 0.95)
    assert np.isclose(gradebook.points_earned.loc["A2", "mt01 with retry"], 0.9)


def test_with_penalty_policy_adds_notes():
    # given
    columns = ["mt01", "mt01 - retry 01", "mt01 - retry 02"]
    p1 = pd.Series(data=[95, 100, 85], index=columns, name="A1")
    p2 = pd.Series(data=[60, 85, 100], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100, 100], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    def cap_at_90(original_scores):
        """A policy that caps all but the first attempt at 90%."""
        return pd.Series(
            np.concatenate(
                [
                    original_scores.values[:1],
                    np.minimum(original_scores.values[1:], 0.9),
                ]
            ),
            index=original_scores.index,
        )

    # when
    take_best(
        gradebook,
        {"mt01 with retry": ["mt01", "mt01 - retry 01", "mt01 - retry 02"]},
        penalty_strategy=cap_at_90,
    )

    # then
    assert gradebook.notes == {
        "A1": {
            "attempts": [
                "Mt01 score: 95.00%. Mt01 - Retry 01 raw score: 100.00%, "
                "after penalty for retrying: 90.00%. Mt01 - Retry 02 score: 85.00%. "
                "Mt01 score (95.00%) used.",
            ]
        },
        "A2": {
            "attempts": [
                "Mt01 score: 60.00%. Mt01 - Retry 01 score: 85.00%. "
                "Mt01 - Retry 02 raw score: 100.00%, "
                "after penalty for retrying: 90.00%. "
                "Mt01 - Retry 02 score (90.00%) used.",
            ]
        },
    }


# lateness strategy ====================================================================


def test_lateness_with_max_lateness_strategy():
    """Test that max_lateness strategy marks overall as late if ANY attempt is late."""
    from gradelib.policies.attempts import max_lateness

    # given - student A1 has on-time first attempt, late retry
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)

    lateness = pd.DataFrame(
        [
            pd.to_timedelta([0, 3600], "s"),  # A1: on-time, then 1hr late
            pd.to_timedelta([0, 0], "s"),  # A2: both on-time
        ],
        columns=columns,
        index=points.index,
    )

    gradebook = gradelib.Gradebook(points, maximums, lateness=lateness)

    # when
    take_best(
        gradebook,
        {"mt01 with retry": ["mt01", "mt01 - retry"]},
        lateness_strategy=max_lateness,
    )

    # then - A1 should be late (max of 0 and 3600), A2 on-time
    assert gradebook.lateness.loc["A1", "mt01 with retry"] == pd.Timedelta(
        3600, unit="s"
    )
    assert gradebook.lateness.loc["A2", "mt01 with retry"] == pd.Timedelta(0, unit="s")
    assert_gradebook_is_sound(gradebook)


def test_lateness_with_lateness_of_best_strategy():
    """Test that lateness_of_best strategy uses only the best attempt's lateness."""
    from gradelib.policies.attempts import lateness_of_best

    # given - A1's best attempt (retry) was late, A2's best (original) was on-time
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)

    lateness = pd.DataFrame(
        [
            pd.to_timedelta([0, 3600], "s"),  # A1: on-time original, late retry
            pd.to_timedelta([0, 7200], "s"),  # A2: on-time original, very late retry
        ],
        columns=columns,
        index=points.index,
    )

    gradebook = gradelib.Gradebook(points, maximums, lateness=lateness)

    # when
    take_best(
        gradebook,
        {"mt01 with retry": ["mt01", "mt01 - retry"]},
        lateness_strategy=lateness_of_best,
    )

    # then
    # A1's best is retry (100 > 95), which was late
    assert gradebook.lateness.loc["A1", "mt01 with retry"] == pd.Timedelta(
        3600, unit="s"
    )
    # A2's best is original (92 > 60), which was on-time
    assert gradebook.lateness.loc["A2", "mt01 with retry"] == pd.Timedelta(0, unit="s")
    assert_gradebook_is_sound(gradebook)


def test_lateness_defaults_to_max_lateness():
    """Test that default behavior is max_lateness strategy."""
    # given
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    points = pd.DataFrame([p1])
    maximums = pd.Series([100, 100], index=columns)

    lateness = pd.DataFrame(
        [
            pd.to_timedelta([0, 3600], "s"),  # on-time original, late retry
        ],
        columns=columns,
        index=points.index,
    )

    gradebook = gradelib.Gradebook(points, maximums, lateness=lateness)

    # when - don't specify lateness_strategy
    take_best(gradebook, {"mt01 with retry": ["mt01", "mt01 - retry"]})

    # then - should use max_lateness (conservative)
    assert gradebook.lateness.loc["A1", "mt01 with retry"] == pd.Timedelta(
        3600, unit="s"
    )
    assert_gradebook_is_sound(gradebook)


def test_lateness_with_penalty_strategy():
    """Test that lateness uses best attempt AFTER penalty is applied."""
    from gradelib.policies.attempts import lateness_of_best

    # given - policy will cap retries at 90%
    columns = ["mt01", "mt01 - retry"]
    p1 = pd.Series(data=[85, 100], index=columns, name="A1")  # retry gets capped to 90
    points = pd.DataFrame([p1])
    maximums = pd.Series([100, 100], index=columns)

    lateness = pd.DataFrame(
        [
            pd.to_timedelta([0, 3600], "s"),  # original on-time, retry late
        ],
        columns=columns,
        index=points.index,
    )

    gradebook = gradelib.Gradebook(points, maximums, lateness=lateness)

    def cap_at_90(original_scores):
        return pd.Series(
            np.concatenate(
                [
                    original_scores.values[:1],
                    np.minimum(original_scores.values[1:], 0.9),
                ]
            ),
            index=original_scores.index,
        )

    # when
    take_best(
        gradebook,
        {"mt01 with retry": ["mt01", "mt01 - retry"]},
        penalty_strategy=cap_at_90,
        lateness_strategy=lateness_of_best,
    )

    # then
    # After penalty: original=85%, retry=90% (capped from 100%)
    # Best is retry (90% > 85%), which was late
    assert gradebook.lateness.loc["A1", "mt01 with retry"] == pd.Timedelta(
        3600, unit="s"
    )
    assert_gradebook_is_sound(gradebook)
