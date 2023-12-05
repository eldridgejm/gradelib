import pytest

import pandas as pd

import gradelib
import gradelib.policies
from gradelib import Points, Percentage


def test_without_forgiveness_or_within_penalizes_all_lates():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [pd.to_timedelta([0, 0, 5000], "s"), pd.to_timedelta([6000, 0, 0], "s")],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradelib.policies.penalize_lates(gradebook)

    assert gradebook.points_earned.loc["A1", "lab01"] == 0
    assert gradebook.points_earned.loc["A2", "hw01"] == 0


def test_with_callable_deduction():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [pd.to_timedelta([6000, 6000, 6000], "s"), pd.to_timedelta([0, 0, 0], "s")],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)
    gradebook.grading_groups = {
        "homeworks": (["hw01", "hw02"], 0.75),
        "labs": (["lab01"], 0.25),
    }

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradebook.options.lateness_fudge = 60 * 5

    def deduction(info):
        return Points(info.number)

    gradelib.policies.penalize_lates(gradebook, deduction=deduction)

    # least to most valuable:
    # A1: hw01 lab01 hw02
    # A2: hw01 hw02 lab01
    # so hw01 receives the greatest deduction

    assert gradebook.points_earned.loc["A1", "hw01"] == 27
    assert gradebook.points_earned.loc["A1", "hw02"] == 89
    assert gradebook.points_earned.loc["A1", "lab01"] == 18


def test_percentage_deduction_applies_percentage_to_points_earned():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [pd.to_timedelta([6000, 6000, 6000], "s"), pd.to_timedelta([0, 0, 0], "s")],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)
    gradebook.grading_groups = {
        "homeworks": (["hw01", "hw02"], 0.75),
        "labs": (["lab01"], 0.25),
    }

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradebook.options.lateness_fudge = 60 * 5

    gradelib.policies.penalize_lates(gradebook, deduction=Percentage(0.5))

    # least to most valuable:
    # A1: hw01 lab01 hw02
    # A2: hw01 hw02 lab01
    # so hw01 receives the greatest deduction

    assert gradebook.points_earned.loc["A1", "hw01"] == 15
    assert gradebook.points_earned.loc["A1", "hw02"] == 45
    assert gradebook.points_earned.loc["A1", "lab01"] == 10


def test_with_callable_deduction_does_not_count_forgiven():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [pd.to_timedelta([6000, 6000, 6000], "s"), pd.to_timedelta([0, 0, 0], "s")],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)

    gradebook.grading_groups = {
        "homeworks": (["hw01", "hw02"], 0.75),
        "labs": (["lab01"], 0.25),
    }

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradebook.options.lateness_fudge = 60 * 5

    def deduction(info):
        return Points(info.number)

    gradelib.policies.penalize_lates(gradebook, deduction=deduction, forgive=1)

    # least to most valuable:
    # A1: hw01, lab01, hw02
    # A2: hw01, hw02, lab01
    # so lab01 receives the greatest deduction, hw02 receives forgiveness

    assert gradebook.points_earned.loc["A1", "hw02"] == 90
    assert gradebook.points_earned.loc["A1", "hw01"] == 28
    assert gradebook.points_earned.loc["A1", "lab01"] == 19


def test_respects_lateness_fudge():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [pd.to_timedelta([0, 0, 50], "s"), pd.to_timedelta([6000, 0, 0], "s")],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradebook.options.lateness_fudge = 60 * 5

    gradelib.policies.penalize_lates(gradebook)

    assert gradebook.points_earned.loc["A2", "hw01"] == 0


def test_within_assignments():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [pd.to_timedelta([0, 0, 5000], "s"), pd.to_timedelta([6000, 0, 0], "s")],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradelib.policies.penalize_lates(gradebook, within=HOMEWORK)

    assert gradebook.points_earned.loc["A2", "hw01"] == 0


def test_within_accepts_callable():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [pd.to_timedelta([0, 0, 5000], "s"), pd.to_timedelta([6000, 0, 0], "s")],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradelib.policies.penalize_lates(gradebook, within=HOMEWORK)

    assert gradebook.points_earned.loc["A2", "hw01"] == 0


def test_with_forgiveness():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [pd.to_timedelta([5000, 0, 5000], "s"), pd.to_timedelta([6000, 0, 0], "s")],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)

    gradebook.grading_groups = {
        "homeworks": (["hw01", "hw02"], 0.75),
        "labs": (["lab01"], 0.25),
    }

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradelib.policies.penalize_lates(gradebook, forgive=1)

    # least to greatest value
    # A1: hw01 hw02 lab01
    # A2: hw01 hw02 lab01

    assert gradebook.points_earned.loc["A1", "hw01"] == 0


def test_with_forgiveness_and_within():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [pd.to_timedelta([5000, 0, 5000], "s"), pd.to_timedelta([6000, 0, 0], "s")],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradelib.policies.penalize_lates(gradebook, within=HOMEWORK, forgive=2)
    gradelib.policies.penalize_lates(gradebook, within=["lab01"])

    assert gradebook.points_earned.loc["A1", "lab01"] == 0


def test_with_forgiveness_forgives_most_valuable_assignments_first_by_default():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[45, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [
            pd.to_timedelta([5000, 5000, 5000], "s"),
            pd.to_timedelta([6000, 5000, 5000], "s"),
        ],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")
    LABS = gradebook.assignments.starting_with("lab")

    gradebook.grading_groups = {
        "homeworks": (HOMEWORK, 0.75),
        "labs": (LABS, 0.25),
    }

    gradelib.policies.penalize_lates(gradebook, within=HOMEWORK + LABS, forgive=2)

    # in order from least to most valuable
    # for AI: hw01, lab01, hw02 -- penalize hw01
    # for A2: hw02, hw01, lab01 -- penalize hw02

    assert gradebook.points_earned.loc["A1", "hw01"] == 0
    assert gradebook.points_earned.loc["A2", "hw02"] == 0


def test_forgives_the_first_n_lates_when_order_by_is_index():
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[45, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [
            pd.to_timedelta([5000, 5000, 5000], "s"),
            pd.to_timedelta([6000, 5000, 5000], "s"),
        ],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")
    LABS = gradebook.assignments.starting_with("lab")

    gradebook.grading_groups = {
        "homeworks": (HOMEWORK, 0.75),
        "labs": (LABS, 0.25),
    }

    gradelib.policies.penalize_lates(
        gradebook, within=HOMEWORK + LABS, forgive=2, order_by="index"
    )

    assert gradebook.points_earned.loc["A1", "lab01"] == 0
    assert gradebook.points_earned.loc["A2", "lab01"] == 0


def test_with_empty_assignment_list_raises():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[45, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [
            pd.to_timedelta([5000, 5000, 5000], "s"),
            pd.to_timedelta([6000, 5000, 5000], "s"),
        ],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)

    # when
    with pytest.raises(ValueError):
        gradelib.policies.penalize_lates(gradebook, within=[])


def test_by_default_takes_into_account_drops():
    columns = ["hw01", "hw02", "lab01", "lab02"]
    p1 = pd.Series(data=[30, 90, 20, 1], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20, 1], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20, 20], index=columns)
    lateness = pd.DataFrame(
        [
            pd.to_timedelta([5000, 5000, 5000, 50000], "s"),
            pd.to_timedelta([6000, 0, 0, 0], "s"),
        ],
        columns=columns,
        index=points_earned.index,
    )

    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)
    gradebook.grading_groups = {
        "homeworks": (gradebook.assignments.starting_with("hw"), 0.75),
        "labs": (gradebook.assignments.starting_with("lab"), 0.25),
    }

    gradebook.dropped.loc["A1", "hw02"] = True

    # after dropping, values from least to greatest
    # A1: hw02, lab02, lab01, hw01
    # A1 has all assignments late. hw01 should receive forgiveness, lab01 and lab02
    # are penalized

    [gradelib.policies.penalize_lates(gradebook, forgive=1)]

    assert gradebook.points_earned.loc["A1", "lab01"] == 0
    assert gradebook.points_earned.loc["A1", "lab02"] == 0


def test_adds_note_for_penalized_assignment():
    # given
    columns = ["hw01", "hw02", "hw03"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [pd.to_timedelta([5000, 5000, 5000], "s"), pd.to_timedelta([6000, 0, 0], "s")],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradebook.grading_groups = {"homeworks": (HOMEWORK, 1)}

    gradelib.policies.penalize_lates(gradebook)

    assert gradebook.notes == {
        "A1": {
            "lates": [
                "Hw02 late. Deduction: 100%. Points earned: 0.",
                "Hw01 late. Deduction: 100%. Points earned: 0.",
                "Hw03 late. Deduction: 100%. Points earned: 0.",
            ]
        },
        "A2": {
            "lates": [
                "Hw01 late. Deduction: 100%. Points earned: 0.",
            ]
        },
    }


def test_with_forgiveness_adds_note_for_forgiven_assignments():
    # given
    columns = ["hw01", "hw02", "hw03"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame(
        [pd.to_timedelta([5000, 5000, 5000], "s"), pd.to_timedelta([6000, 0, 0], "s")],
        columns=columns,
        index=points_earned.index,
    )
    gradebook = gradelib.Gradebook(points_earned, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradebook.grading_groups = {"homeworks": (HOMEWORK, 1)}

    gradelib.policies.penalize_lates(gradebook, forgive=2)

    # least to greatest value
    # A1: hw01 hw02 lab01
    # A2: hw01 hw02 lab01

    assert gradebook.notes == {
        "A1": {
            "lates": [
                "Slip day #1 used on Hw02. Slip days remaining: 1.",
                "Slip day #2 used on Hw01. Slip days remaining: 0.",
                "Hw03 late. Deduction: 100%. Points earned: 0.",
            ]
        },
        "A2": {
            "lates": [
                "Slip day #1 used on Hw01. Slip days remaining: 1.",
            ]
        },
    }
