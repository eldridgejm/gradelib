"""Tests of the Gradebook class."""

import pathlib

import pytest
import pandas as pd
import numpy as np

import gradelib
import gradelib.io.gradescope
import gradelib.io.canvas

# examples setup -----------------------------------------------------------------------

EXAMPLES_DIRECTORY = pathlib.Path(__file__).parent.parent / "examples"
GRADESCOPE_EXAMPLE = gradelib.io.gradescope.read(EXAMPLES_DIRECTORY / "gradescope.csv")
CANVAS_EXAMPLE = gradelib.io.canvas.read(EXAMPLES_DIRECTORY / "canvas.csv")

# the canvas example has Lab 01, which is also in Gradescope. Let's remove it
CANVAS_WITHOUT_LAB_EXAMPLE = gradelib.Gradebook(
    points_earned=CANVAS_EXAMPLE.points_earned.drop(columns="lab 01"),
    points_possible=CANVAS_EXAMPLE.points_possible.drop(index="lab 01"),
    lateness=CANVAS_EXAMPLE.lateness.drop(columns="lab 01"),
    dropped=CANVAS_EXAMPLE.dropped.drop(columns="lab 01"),
)

ROSTER = pd.read_csv(EXAMPLES_DIRECTORY / "egrades.csv", delimiter="\t").set_index(
    "Student ID"
)


# helper functions ---------------------------------------------------------------------


def assert_gradebook_is_sound(gradebook):
    assert (
        gradebook.points_earned.shape
        == gradebook.dropped.shape
        == gradebook.lateness.shape
    )
    assert (gradebook.points_earned.columns == gradebook.dropped.columns).all()
    assert (gradebook.points_earned.columns == gradebook.lateness.columns).all()
    assert (gradebook.points_earned.index == gradebook.dropped.index).all()
    assert (gradebook.points_earned.index == gradebook.lateness.index).all()
    assert (gradebook.points_earned.columns == gradebook.points_possible.index).all()


def as_gradebook_type(gb, gradebook_cls):
    """Creates a Gradebook object from a Gradebook or Gradebook."""
    return gradebook_cls(
        points_earned=gb.points_earned,
        points_possible=gb.points_possible,
        lateness=gb.lateness,
        dropped=gb.dropped,
        notes=gb.notes,
        opts=gb.opts,
    )


# tests: options =======================================================================

# lateness fudge -----------------------------------------------------------------------


def test_lateness_fudge_defaults_to_5_minutes():
    columns = ["hw01", "hw02"]
    p1 = pd.Series(data=[1, 30], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7], index=columns, name="A2")
    l1 = pd.Series(
        data=[pd.Timedelta(seconds=30), pd.Timedelta(seconds=0)],
        index=columns,
        name="A1",
    )
    l2 = pd.Series(
        data=[pd.Timedelta(seconds=30), pd.Timedelta(seconds=60 * 5 + 1)],
        index=columns,
        name="A2",
    )

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50], index=columns)
    lateness = pd.DataFrame([l1, l2])

    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness)

    assert gradebook.late.loc["A1", "hw01"] == False
    assert gradebook.late.loc["A2", "hw02"] == True


def test_lateness_fudge_can_be_changed():
    columns = ["hw01", "hw02"]
    p1 = pd.Series(data=[1, 30], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7], index=columns, name="A2")
    l1 = pd.Series(
        data=[pd.Timedelta(seconds=30), pd.Timedelta(seconds=0)],
        index=columns,
        name="A1",
    )
    l2 = pd.Series(
        data=[pd.Timedelta(seconds=30), pd.Timedelta(seconds=60 * 5 + 1)],
        index=columns,
        name="A2",
    )

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50], index=columns)
    lateness = pd.DataFrame([l1, l2])

    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness)

    assert gradebook.late.loc["A1", "hw01"] == False
    assert gradebook.late.loc["A2", "hw02"] == True

    gradebook.opts.lateness_fudge = 10

    assert gradebook.late.loc["A1", "hw01"] == True
    assert gradebook.late.loc["A2", "hw02"] == True


# tests: properties ====================================================================


# weight -------------------------------------------------------------------------------


def test_weight_defaults_to_being_computed_from_points_possible():
    columns = ["hw01", "hw02", "lab01", "lab02"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.assignment_groups = {
        "homeworks": (gb.assignments.starting_with("hw"), 0.75),
        "labs": (gb.assignments.starting_with("lab"), 0.25),
    }

    assert gb.weight.loc["A1", "hw01"] == 20 / 70
    assert gb.weight.loc["A1", "hw02"] == 50 / 70
    assert gb.weight.loc["A2", "hw01"] == 20 / 70
    assert gb.weight.loc["A2", "hw02"] == 50 / 70


def test_weight_assignments_not_in_a_group_are_nan():
    columns = ["hw01", "hw02", "lab01", "lab02"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.assignment_groups = {
        "homeworks": (gb.assignments.starting_with("hw"), 0.75),
    }

    assert gb.weight.loc["A1", "hw01"] == 20 / 70
    assert gb.weight.loc["A1", "hw02"] == 50 / 70
    assert gb.weight.loc["A2", "hw01"] == 20 / 70
    assert gb.weight.loc["A2", "hw02"] == 50 / 70
    assert np.isnan(gb.weight.loc["A1", "lab01"])
    assert np.isnan(gb.weight.loc["A1", "lab02"])
    assert np.isnan(gb.weight.loc["A2", "lab01"])
    assert np.isnan(gb.weight.loc["A2", "lab02"])


def test_weight_takes_drops_into_account():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)
    gb.dropped.loc["A1", "hw01"] = True
    gb.dropped.loc["A2", "hw01"] = True
    gb.dropped.loc["A2", "hw03"] = True

    gb.assignment_groups = {
        "homeworks": (gb.assignments.starting_with("hw"), 0.75),
        "labs": (gb.assignments.starting_with("lab"), 0.25),
    }

    assert gb.weight.loc["A1", "hw01"] == 0.0
    assert gb.weight.loc["A1", "hw02"] == 50 / 80
    assert gb.weight.loc["A2", "hw01"] == 0.0
    assert gb.weight.loc["A2", "hw02"] == 1.0


def test_weight_with_normalization():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.assignment_groups = {
        "homeworks": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("hw")),
            0.75,
        ),
        "labs": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("lab")),
            0.25,
        ),
    }

    assert gb.weight.loc["A1", "hw01"] == 1 / 3
    assert gb.weight.loc["A1", "hw02"] == 1 / 3
    assert gb.weight.loc["A2", "lab01"] == 1.0


def test_weight_with_normalization_and_drops():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.dropped.loc["A1", "hw02"] = True
    gb.dropped.loc["A2", "hw01"] = True
    gb.dropped.loc["A2", "hw03"] = True

    gb.assignment_groups = {
        "homeworks": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("hw")),
            0.75,
        ),
        "labs": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("lab")),
            0.25,
        ),
    }

    assert gb.weight.loc["A1", "hw01"] == 1 / 2
    assert gb.weight.loc["A1", "hw02"] == 0.0
    assert gb.weight.loc["A2", "hw02"] == 1.0


def test_weight_with_custom_weights():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.assignment_groups = {
        "homeworks": gradelib.AssignmentGroup(
            {
                "hw01": 0.3,
                "hw02": 0.5,
                "hw03": 0.2,
            },
            0.75,
        ),
        "labs": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("lab")),
            0.25,
        ),
    }

    assert gb.weight.loc["A1", "hw01"] == 0.3
    assert gb.weight.loc["A1", "hw02"] == 0.5
    assert gb.weight.loc["A2", "hw02"] == 0.5


def test_weight_with_custom_weights_and_drops():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.dropped.loc["A1", "hw02"] = True
    gb.dropped.loc["A2", "hw01"] = True
    gb.dropped.loc["A2", "hw03"] = True

    gb.assignment_groups = {
        "homeworks": gradelib.AssignmentGroup(
            {
                "hw01": 0.3,
                "hw02": 0.5,
                "hw03": 0.2,
            },
            0.75,
        ),
        "labs": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("lab")),
            0.25,
        ),
    }

    assert gb.weight.loc["A1", "hw01"] == 0.3 / 0.5
    assert gb.weight.loc["A1", "hw02"] == 0.0
    assert gb.weight.loc["A1", "hw03"] == 0.2 / 0.5
    assert gb.weight.loc["A2", "hw02"] == 1.0


# overall_weight -----------------------------------------------------------------------


def test_overall_weight_defaults_to_being_computed_from_points_possible():
    columns = ["hw01", "hw02", "lab01", "lab02"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.assignment_groups = {
        "homeworks": (gb.assignments.starting_with("hw"), 0.75),
        "labs": (gb.assignments.starting_with("lab"), 0.25),
    }

    assert gb.overall_weight.loc["A1", "hw01"] == 20 / 70 * 0.75
    assert gb.overall_weight.loc["A1", "hw02"] == 50 / 70 * 0.75
    assert gb.overall_weight.loc["A2", "hw01"] == 20 / 70 * 0.75
    assert gb.overall_weight.loc["A2", "hw02"] == 50 / 70 * 0.75


def test_overall_weight_assignments_not_in_a_group_are_nan():
    columns = ["hw01", "hw02", "lab01", "lab02"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.assignment_groups = {
        "homeworks": (gb.assignments.starting_with("hw"), 0.75),
    }

    assert gb.overall_weight.loc["A1", "hw01"] == 20 / 70 * 0.75
    assert gb.overall_weight.loc["A1", "hw02"] == 50 / 70 * 0.75
    assert gb.overall_weight.loc["A2", "hw01"] == 20 / 70 * 0.75
    assert gb.overall_weight.loc["A2", "hw02"] == 50 / 70 * 0.75
    assert np.isnan(gb.overall_weight.loc["A1", "lab01"])
    assert np.isnan(gb.overall_weight.loc["A1", "lab02"])
    assert np.isnan(gb.overall_weight.loc["A2", "lab01"])
    assert np.isnan(gb.overall_weight.loc["A2", "lab02"])


def test_overall_weight_takes_drops_into_account():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)
    gb.dropped.loc["A1", "hw01"] = True
    gb.dropped.loc["A2", "hw01"] = True
    gb.dropped.loc["A2", "hw03"] = True

    gb.assignment_groups = {
        "homeworks": (gb.assignments.starting_with("hw"), 0.75),
        "labs": (gb.assignments.starting_with("lab"), 0.25),
    }

    assert gb.overall_weight.loc["A1", "hw01"] == 0.0 * 0.75
    assert gb.overall_weight.loc["A1", "hw02"] == 50 / 80 * 0.75
    assert gb.overall_weight.loc["A2", "hw01"] == 0.0 * 0.75
    assert gb.overall_weight.loc["A2", "hw02"] == 1.0 * 0.75


def test_overall_weight_with_normalization():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.assignment_groups = {
        "homeworks": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("hw")),
            0.75,
        ),
        "labs": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("lab")),
            0.25,
        ),
    }

    assert gb.overall_weight.loc["A1", "hw01"] == 1 / 3 * 0.75
    assert gb.overall_weight.loc["A1", "hw02"] == 1 / 3 * 0.75
    assert gb.overall_weight.loc["A2", "lab01"] == 1.0 * 0.25


def test_overall_weight_with_normalization_and_drops():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.dropped.loc["A1", "hw02"] = True
    gb.dropped.loc["A2", "hw01"] = True
    gb.dropped.loc["A2", "hw03"] = True

    gb.assignment_groups = {
        "homeworks": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("hw")),
            0.75,
        ),
        "labs": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("lab")),
            0.25,
        ),
    }

    assert gb.overall_weight.loc["A1", "hw01"] == 1 / 2 * 0.75
    assert gb.overall_weight.loc["A1", "hw02"] == 0.0 * 0.75
    assert gb.overall_weight.loc["A2", "hw02"] == 1.0 * 0.75


def test_overall_weight_with_custom_weights():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.assignment_groups = {
        "homeworks": gradelib.AssignmentGroup(
            {
                "hw01": 0.3,
                "hw02": 0.5,
                "hw03": 0.2,
            },
            0.75,
        ),
        "labs": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("lab")),
            0.25,
        ),
    }

    assert gb.overall_weight.loc["A1", "hw01"] == 0.3 * 0.75
    assert gb.overall_weight.loc["A1", "hw02"] == 0.5 * 0.75
    assert gb.overall_weight.loc["A2", "hw02"] == 0.5 * 0.75


def test_overall_weight_with_custom_weights_and_drops():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.dropped.loc["A1", "hw02"] = True
    gb.dropped.loc["A2", "hw01"] = True
    gb.dropped.loc["A2", "hw03"] = True

    gb.assignment_groups = {
        "homeworks": gradelib.AssignmentGroup(
            {
                "hw01": 0.3,
                "hw02": 0.5,
                "hw03": 0.2,
            },
            0.75,
        ),
        "labs": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("lab")),
            0.25,
        ),
    }

    assert gb.overall_weight.loc["A1", "hw01"] == 0.3 / 0.5 * 0.75
    assert gb.overall_weight.loc["A1", "hw02"] == 0.0 * 0.75
    assert gb.overall_weight.loc["A1", "hw03"] == 0.2 / 0.5 * 0.75
    assert gb.overall_weight.loc["A2", "hw02"] == 1.0 * 0.75


# value --------------------------------------------------------------------------------


def test_value_with_default_weights():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.assignment_groups = {
        "homeworks": (gb.assignments.starting_with("hw"), 0.75),
        "labs": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("lab")),
            0.25,
        ),
    }

    assert gb.value.loc["A1", "hw01"] == 10 / 20 * 20 / 100 * 0.75
    assert gb.value.loc["A1", "hw02"] == 30 / 50 * 50 / 100 * 0.75
    assert gb.value.loc["A1", "lab01"] == 25 / 40 * 0.25


def test_value_with_drops():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)
    gb.dropped.loc["A1", "hw02"] = True
    gb.dropped.loc["A2", "hw01"] = True
    gb.dropped.loc["A2", "hw03"] = True

    gb.assignment_groups = {
        "homeworks": (gb.assignments.starting_with("hw"), 0.75),
        "labs": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("lab")),
            0.25,
        ),
    }

    assert gb.value.loc["A1", "hw01"] == 10 / 20 * 20 / 50 * 0.75
    assert gb.value.loc["A1", "hw02"] == 0.0
    assert gb.value.loc["A1", "lab01"] == 25 / 40 * 0.25


def test_value_with_custom_assignment_weights():
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[10, 30, 20, 25], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40, 30, 10], index=columns, name="A2")

    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50, 30, 40], index=columns)

    gb = gradelib.Gradebook(points_earned, points_possible)

    gb.assignment_groups = {
        "homeworks": gradelib.AssignmentGroup(
            {
                "hw01": 0.3,
                "hw02": 0.5,
                "hw03": 0.2,
            },
            0.75,
        ),
        "labs": gradelib.AssignmentGroup(
            gradelib.normalize(gb.assignments.starting_with("lab")),
            0.25,
        ),
    }

    assert gb.value.loc["A1", "hw01"] == 10 / 20 * 0.3 * 0.75
    assert gb.value.loc["A1", "hw02"] == 30 / 50 * 0.5 * 0.75
    assert gb.value.loc["A1", "lab01"] == 25 / 40 * 0.25


# overall_score ------------------------------------------------------------------------


def test_overall_score_respects_group_weighting():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.assignment_groups = {
        "homeworks": (HOMEWORKS, 0.6),
        "labs": (["lab01"], 0.4),
    }

    # then
    pd.testing.assert_series_equal(
        gradebook.overall_score,
        pd.Series(
            [121 / 152 * 0.6 + 20 / 20 * 0.4, 24 / 152 * 0.6 + 20 / 20 * 0.4],
            index=gradebook.students,
        ),
    )


def test_overall_score_respects_dropped_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A2", "hw03"] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.assignment_groups = {
        "homeworks": (HOMEWORKS, 0.6),
        "labs": (["lab01"], 0.4),
    }

    # then
    pd.testing.assert_series_equal(
        gradebook.overall_score,
        pd.Series(
            [91 / 102 * 0.6 + 20 / 20 * 0.4, 9 / 52 * 0.6 + 20 / 20 * 0.40],
            index=gradebook.students,
        ),
    )


# letter_grades ------------------------------------------------------------------------


def test_letter_grades_respects_scale():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A2", "hw03"] = True

    gradebook.scale = {
        "A+": 0.9,
        "A": 0.8,
        "A-": 0.7,
        "B+": 0.6,
        "B": 0.5,
        "B-": 0.4,
        "C+": 0.35,
        "C": 0.3,
        "C-": 0.2,
        "D": 0.1,
        "F": 0,
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.assignment_groups = {
        "homeworks": gradelib.AssignmentGroup(gradelib.normalize(HOMEWORKS), 0.6),
        "labs": (["lab01"], 0.4),
    }

    # then
    # .805 and .742
    pd.testing.assert_series_equal(
        gradebook.letter_grades, pd.Series(["A", "A-"], index=gradebook.students)
    )


# tests: groups ========================================================================


# default_groups -----------------------------------------------------------------------


def test_default_groups_one_assignment_per_group_equally_weighted():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # then
    assert gradebook.default_groups == {
        "hw01": gradelib.AssignmentGroup({"hw01": 1}, group_weight=0.25),
        "hw02": gradelib.AssignmentGroup({"hw02": 1}, group_weight=0.25),
        "hw03": gradelib.AssignmentGroup({"hw03": 1}, group_weight=0.25),
        "lab01": gradelib.AssignmentGroup({"lab01": 1}, group_weight=0.25),
    }


# groups -------------------------------------------------------------------------------


def test_groups_setter_allows_three_tuple_form():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    gradebook.assignment_groups = {
        "homeworks": (["hw01", "hw02", "hw03"], 0.5),
        "labs": (["lab01"], 0.5),
    }

    # then
    hw_weights = {"hw01": 2 / 152, "hw02": 50 / 152, "hw03": 100 / 152}
    lab_weights = {"lab01": 1}
    assert gradebook.assignment_groups == {
        "homeworks": gradelib.AssignmentGroup(hw_weights, group_weight=0.5),
        "labs": gradelib.AssignmentGroup(lab_weights, group_weight=0.5),
    }


def test_groups_setter_allows_two_tuple_form():
    # given
    columns = ["hw01", "hw02", "hw03", "midterm"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    gradebook.assignment_groups = {
        "homeworks": (["hw01", "hw02", "hw03"], 0.5),
        "midterm": (0.5),
    }

    # then
    hw_weights = {"hw01": 2 / 152, "hw02": 50 / 152, "hw03": 100 / 152}
    assert gradebook.assignment_groups == {
        "homeworks": gradelib.AssignmentGroup(hw_weights, group_weight=0.5),
        "midterm": gradelib.AssignmentGroup({"midterm": 1}, group_weight=0.5),
    }


def test_groups_setter_allows_callable_for_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    HOMEWORKS_LAZY = lambda asmts: asmts.starting_with("hw")
    LABS_LAZY = lambda asmts: asmts.starting_with("lab")

    gradebook.assignment_groups = {
        "homeworks": (HOMEWORKS_LAZY, 0.5),
        "labs": (LABS_LAZY, 0.5),
    }

    # then
    hw_weights = {"hw01": 2 / 152, "hw02": 50 / 152, "hw03": 100 / 152}
    lab_weights = {"lab01": 1}
    assert gradebook.assignment_groups == {
        "homeworks": gradelib.AssignmentGroup(hw_weights, group_weight=0.5),
        "labs": gradelib.AssignmentGroup(lab_weights, group_weight=0.5),
    }


# group_points_possible_after_drops ----------------------------------------------------


def test_group_points_respects_dropped_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A2", "hw03"] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.assignment_groups = {
        "homeworks": (HOMEWORKS, 0.5),
        "labs": (["lab01"], 0.5),
    }

    # then

    pd.testing.assert_frame_equal(
        gradebook.group_points_possible_after_drops,
        pd.DataFrame(
            [[102, 20], [52, 20]],
            index=gradebook.students,
            columns=["homeworks", "labs"],
        ),
    )


def test_group_points_raises_if_all_assignments_in_a_group_are_dropped():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)
    gradebook.dropped.loc["A1", "lab01"] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.assignment_groups = {
        "homeworks": (HOMEWORKS, 0.5),
        "labs": (["lab01"], 0.5),
    }

    # then
    with pytest.raises(ValueError):
        gradebook.group_points_possible_after_drops


# group_scores -------------------------------------------------------------------------


def test_group_scores_raises_if_all_assignments_in_a_group_are_dropped():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)
    gradebook.dropped.loc["A1", "lab01"] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.assignment_groups = {
        "homeworks": (HOMEWORKS, 0.5),
        "labs": (["lab01"], 0.5),
    }

    # then
    with pytest.raises(ValueError):
        gradebook.group_scores


def test_group_scores_respects_dropped_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A2", "hw03"] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.assignment_groups = {
        "homeworks": (HOMEWORKS, 0.5),
        "labs": (["lab01"], 0.5),
    }

    # then
    pd.testing.assert_frame_equal(
        gradebook.group_scores,
        pd.DataFrame(
            [[91 / 102, 20 / 20], [9 / 52, 20 / 20]],
            index=gradebook.students,
            columns=["homeworks", "labs"],
        ),
    )


def test_group_scores_with_assignment_weights():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[0, 15, 30, 20], index=columns, name="A1")
    p2 = pd.Series(data=[0, 0, 0, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([30, 30, 30, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    homework_weights = {"hw01": 0.5, "hw02": 0.25, "hw03": 0.25}

    gradebook.assignment_groups = {
        "homeworks": (homework_weights, 0.5),
        "labs": (["lab01"], 0.5),
    }

    # then
    pd.testing.assert_frame_equal(
        gradebook.group_scores,
        pd.DataFrame(
            [[0.125 + 0.25, 1], [0, 20 / 20]],
            index=gradebook.students,
            columns=["homeworks", "labs"],
        ),
    )


# tests: add/remove assignments ========================================================

# restrict_to_assignments --------------------------------------------------------------


def test_restrict_to_assignments():
    # when
    example = GRADESCOPE_EXAMPLE.copy()
    example.restrict_to_assignments(["homework 01", "homework 02"])

    # then
    assert set(example.assignments) == {"homework 01", "homework 02"}
    assert_gradebook_is_sound(example)


def test_restrict_to_assignments_raises_if_assignment_does_not_exist():
    # given
    example = GRADESCOPE_EXAMPLE.copy()
    assignments = ["homework 01", "this aint an assignment"]

    # then
    with pytest.raises(KeyError):
        example.restrict_to_assignments(assignments)


def test_restrict_to_assignments_updates_groups_and_renormalizes_weights():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01", "midterm"]
    p1 = pd.Series(data=[1, 30, 90, 20, 30], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20, 30], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20, 30], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    gradebook.assignment_groups = {
        "homeworks": ({"hw01": 0.25, "hw02": 0.5, "hw03": 0.25}, 0.5),
        "labs": (gradebook.assignments.starting_with("lab"), 0.25),
        "midterm": 0.25
    }

    # when
    gradebook.restrict_to_assignments(["hw01", "hw02", "midterm"])

    # then
    # - removes labs
    # - renormalizes homework group assignment weights
    # - renormalizes group weights, too
    assert gradebook.assignment_groups == {
        "homeworks": gradelib.AssignmentGroup(
            # assignment weights are renormalized to one
            {"hw01": 0.25/0.75, "hw02": 0.5/0.75}, 0.5/0.75
        ),
        "midterm": gradelib.AssignmentGroup(
            # assignment weights are renormalized to one
            {"midterm": 1}, 0.25/0.75
        ),
    }

# remove_assignments -------------------------------------------------------------------


def test_remove_assignments():
    # when
    example = GRADESCOPE_EXAMPLE.copy()
    example.remove_assignments(example.assignments.starting_with("lab"))

    # then
    assert set(example.assignments) == {
        "homework 01",
        "homework 02",
        "homework 03",
        "homework 04",
        "homework 05",
        "homework 06",
        "homework 07",
        "project 01",
        "project 02",
    }
    assert_gradebook_is_sound(example)


def test_remove_assignments_raises_if_assignment_does_not_exist():
    # given
    assignments = ["homework 01", "this aint an assignment"]
    example = GRADESCOPE_EXAMPLE.copy()

    # then
    with pytest.raises(KeyError):
        example.remove_assignments(assignments)


# add_assignment -----------------------------------------------------------------------


def test_add_assignment():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    assignment_points_earned = pd.Series([10, 20], index=["A1", "A2"])
    assignment_max = 20
    assignment_late = pd.Series(
        [pd.Timedelta(days=2), pd.Timedelta(days=0)], index=["A1", "A2"]
    )
    assignment_dropped = pd.Series([False, True], index=["A1", "A2"])

    # when
    gradebook.add_assignment(
        "new",
        assignment_points_earned,
        points_possible=20,
        lateness=assignment_late,
        dropped=assignment_dropped,
    )

    # then
    assert len(gradebook.assignments) == 5
    assert gradebook.points_earned.loc["A1", "new"] == 10
    assert gradebook.points_possible.loc["new"] == 20
    assert isinstance(gradebook.lateness.index[0], gradelib.Student)
    assert isinstance(gradebook.dropped.index[0], gradelib.Student)


def test_add_assignment_default_none_dropped_or_late():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    assignment_points_earned = pd.Series([10, 20], index=["A1", "A2"])
    assignment_max = 20

    # when
    gradebook.add_assignment(
        "new",
        assignment_points_earned,
        20,
    )

    # then
    assert gradebook.late.loc["A1", "new"] == False
    assert gradebook.dropped.loc["A1", "new"] == False


def test_add_assignment_raises_on_missing_student():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # A2 is missing
    assignment_points_earned = pd.Series([10], index=["A1"])
    assignment_max = 20

    # when
    with pytest.raises(ValueError):
        gradebook.add_assignment(
            "new",
            assignment_points_earned,
            20,
        )


def test_add_assignment_raises_on_unknown_student():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # foo is unknown
    assignment_points_earned = pd.Series([10, 20, 30], index=["A1", "A2", "A3"])
    assignment_max = 20

    # when
    with pytest.raises(ValueError):
        gradebook.add_assignment(
            "new",
            assignment_points_earned,
            20,
        )


def test_add_assignment_raises_if_duplicate_name():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    assignment_points_earned = pd.Series([10, 20], index=["A1", "A2"])

    # when
    with pytest.raises(ValueError):
        gradebook.add_assignment(
            "hw01",
            assignment_points_earned,
            20,
        )


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
    gradebook.combine_assignment_parts({"hw01": HOMEWORK_01_PARTS})

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
    gradebook.combine_assignment_parts(
        {"hw01": HOMEWORK_01_PARTS, "hw02": HOMEWORK_02_PARTS}
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


def test_combine_assignment_parts_with_callable():
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

    def assignment_to_key(s):
        return s.split("-")[0].strip()

    # when
    gradebook.combine_assignment_parts(assignment_to_key)

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


def test_combine_assignment_parts_with_list_of_prefixes():
    """test that points_earned / points_possible are added across unified assignments"""
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "hw02 - testing", "lab 01"]
    p1 = pd.Series(data=[1, 30, 90, 20, 10], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20, 10], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20, 10], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # when
    gradebook.combine_assignment_parts(["hw01", "hw02"])

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
    gradebook.combine_assignment_parts({"hw01": HOMEWORK_01_PARTS})

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
        gradebook.combine_assignment_parts({"hw01": HOMEWORK_01_PARTS})


def test_combine_assignment_parts_copies_attributes():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)
    gradebook.notes = {"A1": ["ok"]}

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    gradebook.combine_assignment_parts({"hw01": HOMEWORK_01_PARTS})


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
    PARTS = gradebook.assignments.starting_with("mt")
    gradebook.combine_assignment_versions({"midterm": columns})

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
    PARTS = gradebook.assignments.starting_with("mt")
    gradebook.combine_assignment_versions({"midterm": columns})

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
    PARTS = gradebook.assignments.starting_with("mt")

    with pytest.raises(ValueError):
        gradebook.combine_assignment_versions({"midterm": columns})


def test_combine_assignment_versions_raises_if_points_earned_in_multiple_versions():
    # given
    columns = ["mt - version a", "mt - version b", "mt - version c"]
    p1 = pd.Series(data=[50, 20, np.nan], index=columns, name="A1")
    p2 = pd.Series(data=[np.nan, 30, np.nan], index=columns, name="A2")
    p3 = pd.Series(data=[np.nan, np.nan, 40], index=columns, name="A3")
    points_earned = pd.DataFrame([p1, p2, p3])
    points_possible = pd.Series([50, 50, 40], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # when
    PARTS = gradebook.assignments.starting_with("mt")

    with pytest.raises(ValueError):
        gradebook.combine_assignment_versions({"midterm": columns})


def test_combine_assignment_versions_raises_if_any_version_is_late():
    # given
    columns = ["mt - version a", "mt - version b", "mt - version c"]
    p1 = pd.Series(data=[50, np.nan, np.nan], index=columns, name="A1")
    p2 = pd.Series(data=[np.nan, 30, np.nan], index=columns, name="A2")
    p3 = pd.Series(data=[np.nan, np.nan, 40], index=columns, name="A3")
    points_earned = pd.DataFrame([p1, p2, p3])
    points_possible = pd.Series([50, 50, 40], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    gradebook.lateness.loc["A1", "mt - version a"] = pd.Timedelta(days=3)

    # when
    PARTS = gradebook.assignments.starting_with("mt")

    with pytest.raises(ValueError):
        gradebook.combine_assignment_versions({"midterm": columns})


# rename_assignments -------------------------------------------------------------------


def test_rename_assignments_simple_example():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)
    gradebook.notes = {"A1": ["ok"]}

    gradebook.rename_assignments(
        {
            "hw01": "homework 01",
            "hw01 - programming": "homework 01 - programming",
        }
    )

    assert "homework 01" in gradebook.assignments
    assert "hw01" not in gradebook.assignments
    assert "homework 01 - programming" in gradebook.assignments
    assert "hw01 - programming" not in gradebook.assignments

    assert gradebook.points_earned.loc["A1", "homework 01"] == 1

    assert_gradebook_is_sound(gradebook)


def test_rename_assignments_raises_error_on_name_clash():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)
    gradebook.notes = {"A1": ["ok"]}

    with pytest.raises(ValueError):
        gradebook.rename_assignments(
            {"hw01": "hw02"},
        )


def test_rename_assignments_allows_swapping_names():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)
    gradebook.notes = {"A1": ["ok"]}

    gradebook.rename_assignments(
        {
            "hw01": "hw02",
            "hw02": "hw01",
        }
    )

    assert gradebook.points_earned.loc["A1", "hw01"] == 90
    assert gradebook.points_earned.loc["A1", "hw02"] == 1
    assert gradebook.points_earned.loc["A2", "hw01"] == 15
    assert gradebook.points_earned.loc["A2", "hw02"] == 2

    assert_gradebook_is_sound(gradebook)


# test: misc. methods ==================================================================


# restrict_to_pids ---------------------------------------------------------------------


def test_restrict_to_pids():
    # when
    example = GRADESCOPE_EXAMPLE.copy()
    example.restrict_to_pids(ROSTER.index)

    # then
    assert len(example.pids) == 3
    assert_gradebook_is_sound(example)


def test_restrict_to_pids_raises_if_pid_does_not_exist():
    # given
    pids = ["A12345678", "ADNEDNE00"]
    example = GRADESCOPE_EXAMPLE.copy()

    # when
    with pytest.raises(KeyError):
        example.restrict_to_pids(pids)


# find_student -------------------------------------------------------------------------


def test_find_student_is_case_insensitive():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    points_earned.index = [
        gradelib.Student("A1", "Justin Eldridge"),
        gradelib.Student("A2", "Barack Obama"),
    ]
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # when
    s = gradebook.find_student("justin")

    # then
    assert s == points_earned.index[0]


def test_find_student_is_case_insensitive_with_capitalized_query():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    points_earned.index = [
        gradelib.Student("A1", "Justin Eldridge"),
        gradelib.Student("A2", "Barack Obama"),
    ]
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # when
    s = gradebook.find_student("Justin")

    # then
    assert s == points_earned.index[0]


def test_find_student_raises_on_multiple_matches():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    points_earned.index = [
        gradelib.Student("A1", "Justin Eldridge"),
        gradelib.Student("A2", "Justin Other"),
    ]
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # when
    with pytest.raises(ValueError):
        gradebook.find_student("justin")


def test_find_student_raises_on_no_match():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    points_earned.index = [
        gradelib.Student("A1", "Justin Eldridge"),
        gradelib.Student("A2", "Justin Other"),
    ]
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # when
    with pytest.raises(ValueError):
        gradebook.find_student("steve")


# tests: free functions ================================================================

# combine_gradebooks -------------------------------------------------------------------


def test_combine_gradebooks_with_restrict_to_pids():
    # when
    combined = gradelib.combine_gradebooks(
        [GRADESCOPE_EXAMPLE, CANVAS_WITHOUT_LAB_EXAMPLE],
        restrict_to_pids=ROSTER.index,
    )

    # then
    assert "homework 01" in combined.assignments
    assert "midterm exam" in combined.assignments
    assert_gradebook_is_sound(combined)


def test_combine_gradebooks_raises_if_duplicate_assignments():
    # the canvas example and the gradescope example both have lab 01.
    # when
    with pytest.raises(ValueError):
        combined = gradelib.combine_gradebooks([GRADESCOPE_EXAMPLE, CANVAS_EXAMPLE])


def test_combine_gradebooks_raises_if_indices_do_not_match():
    # when
    with pytest.raises(ValueError):
        combined = gradelib.combine_gradebooks(
            [CANVAS_WITHOUT_LAB_EXAMPLE, GRADESCOPE_EXAMPLE]
        )


def test_combine_gradebooks_concatenates_groups():
    ex_1 = GRADESCOPE_EXAMPLE.copy()
    ex_2 = CANVAS_WITHOUT_LAB_EXAMPLE.copy()

    ex_1.assignment_groups = {
        "homeworks": (ex_1.assignments.starting_with("home"), 0.25),
        "labs": (ex_1.assignments.starting_with("lab"), 0.25),
    }

    ex_2.assignment_groups = {"exams": (["midterm exam", "final exam"], 0.5)}

    combined = gradelib.combine_gradebooks(
        [ex_1, ex_2],
        restrict_to_pids=ROSTER.index,
    )

    assert combined.assignment_groups == {
        **ex_1.assignment_groups,
        **ex_2.assignment_groups,
    }


def test_combine_gradebooks_raises_if_group_names_conflict():
    ex_1 = GRADESCOPE_EXAMPLE.copy()
    ex_2 = CANVAS_WITHOUT_LAB_EXAMPLE.copy()

    ex_1.assignment_groups = {
        "homeworks": (ex_1.assignments.starting_with("home"), 0.25),
        "labs": (ex_1.assignments.starting_with("lab"), 0.25),
    }

    ex_2.assignment_groups = {"homeworks": (["midterm exam", "final exam"], 0.5)}

    with pytest.raises(ValueError):
        combined = gradelib.combine_gradebooks(
            [ex_1, ex_2],
            restrict_to_pids=ROSTER.index,
        )


def test_combine_gradebooks_uses_existing_options_if_all_the_same():
    ex_1 = GRADESCOPE_EXAMPLE.copy()
    ex_2 = CANVAS_WITHOUT_LAB_EXAMPLE.copy()

    ex_1.opts.lateness_fudge = 789
    ex_2.opts.lateness_fudge = 789

    combined = gradelib.combine_gradebooks(
        [ex_1, ex_2],
        restrict_to_pids=ROSTER.index,
    )

    assert combined.opts.lateness_fudge == 789


def test_combine_gradebooks_raises_if_options_do_not_match():
    ex_1 = GRADESCOPE_EXAMPLE.copy()
    ex_2 = CANVAS_WITHOUT_LAB_EXAMPLE.copy()

    ex_1.opts.lateness_fudge = 5000
    ex_2.opts.lateness_fudge = 6000

    with pytest.raises(ValueError):
        combined = gradelib.combine_gradebooks(
            [ex_1, ex_2],
            restrict_to_pids=ROSTER.index,
        )


def test_combine_gradebooks_uses_existing_scales_if_all_the_same():
    ex_1 = GRADESCOPE_EXAMPLE.copy()
    ex_2 = CANVAS_WITHOUT_LAB_EXAMPLE.copy()

    import gradelib.scales

    ex_1.scale = gradelib.scales.ROUNDED_DEFAULT_SCALE
    ex_2.scale = gradelib.scales.ROUNDED_DEFAULT_SCALE

    combined = gradelib.combine_gradebooks(
        [ex_1, ex_2],
        restrict_to_pids=ROSTER.index,
    )

    assert combined.scale == gradelib.scales.ROUNDED_DEFAULT_SCALE


def test_combine_gradebooks_raises_if_scales_do_not_match():
    ex_1 = GRADESCOPE_EXAMPLE.copy()
    ex_2 = CANVAS_WITHOUT_LAB_EXAMPLE.copy()

    ex_2.scale = gradelib.scales.ROUNDED_DEFAULT_SCALE

    with pytest.raises(ValueError):
        combined = gradelib.combine_gradebooks(
            [ex_1, ex_2],
            restrict_to_pids=ROSTER.index,
        )


def test_combine_gradebooks_concatenates_notes():
    # when
    example_1 = GRADESCOPE_EXAMPLE.copy()
    example_2 = CANVAS_WITHOUT_LAB_EXAMPLE.copy()

    example_1.notes = {"A1": {"drop": ["foo", "bar"]}, "A2": {"misc": ["baz"]}}

    example_2.notes = {
        "A1": {"drop": ["baz", "quux"]},
        "A2": {"late": ["ok"]},
        "A3": {"late": ["message"]},
    }

    combined = gradelib.combine_gradebooks(
        [example_1, example_2], restrict_to_pids=ROSTER.index
    )

    # then
    assert combined.notes == {
        "A1": {"drop": ["foo", "bar", "baz", "quux"]},
        "A2": {"misc": ["baz"], "late": ["ok"]},
        "A3": {"late": ["message"]},
    }
