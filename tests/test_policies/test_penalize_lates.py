import pytest

import pandas as pd

import gradelib
from gradelib import Points, Percentage


def test_penalize_lates_without_forgiveness_or_within_penalizes_all_lates():
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

    result = gradebook.apply(gradelib.policies.PenalizeLates())

    assert result.points_earned.loc["A1", "lab01"] == 0
    assert result.points_earned.loc["A2", "hw01"] == 0


def test_penalize_lates_with_callable_deduction():
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

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradebook.opts.lateness_fudge = 60 * 5

    def deduction(info):
        return Points(info.number)

    result = gradebook.apply(gradelib.policies.PenalizeLates(deduction=deduction))

    # least to most valuable:
    # A1: hw01 hw02 lab01
    # A2: hw01 hw02 lab01
    # so hw01 receives the greatest deduction

    assert result.points_earned.loc["A1", "hw01"] == 27
    assert result.points_earned.loc["A1", "hw02"] == 88
    assert result.points_earned.loc["A1", "lab01"] == 19


def test_penalize_lates_with_callable_deduction_does_not_count_forgiven():
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

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradebook.opts.lateness_fudge = 60 * 5

    def deduction(info):
        return Points(info.number)

    result = gradebook.apply(
        gradelib.policies.PenalizeLates(deduction=deduction, forgive=1)
    )

    # least to most valuable:
    # A1: hw01 hw02 lab01
    # A2: hw01 hw02 lab01
    # so hw01 receives the greatest deduction, lab01 receives forgiveness

    assert result.points_earned.loc["A1", "hw02"] == 89
    assert result.points_earned.loc["A1", "hw01"] == 28
    assert result.points_earned.loc["A1", "lab01"] == 20


def test_penalize_lates_respects_lateness_fudge():
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

    gradebook.opts.lateness_fudge = 60 * 5

    result = gradebook.apply(gradelib.policies.PenalizeLates())

    assert result.points_earned.loc["A2", "hw01"] == 0


def test_penalize_lates_within_assignments():
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

    result = gradebook.apply(gradelib.policies.PenalizeLates(within=HOMEWORK))

    assert result.points_earned.loc["A2", "hw01"] == 0


def test_penalize_lates_within_accepts_callable():
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

    HOMEWORK = lambda asmts: asmts.starting_with("hw")

    result = gradebook.apply(gradelib.policies.PenalizeLates(within=HOMEWORK))

    assert result.points_earned.loc["A2", "hw01"] == 0


def test_penalize_lates_with_forgiveness():
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

    result = gradebook.apply(gradelib.policies.PenalizeLates(forgive=1))

    # least to greatest value
    # A1: hw01 hw02 lab01
    # A2: hw01 hw02 lab01

    assert result.points_earned.loc["A1", "hw01"] == 0


def test_penalize_lates_with_forgiveness_and_within():
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

    result = gradebook.apply(
        [
            gradelib.policies.PenalizeLates(within=HOMEWORK, forgive=2),
            gradelib.policies.PenalizeLates(within=["lab01"]),
        ]
    )

    assert result.points_earned.loc["A1", "lab01"] == 0


def test_penalize_lates_with_forgiveness_forgives_most_valuable_assignments_first_by_default():
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

    gradebook.assignment_groups = {
        "homeworks": (HOMEWORK, 0.75),
        "labs": (LABS, 0.25),
    }

    result = gradelib.policies.PenalizeLates(within=HOMEWORK + LABS, forgive=2)(
        gradebook
    )

    # in order from least to most valuable
    # for AI: hw01, lab01, hw02 -- penalize hw01
    # for A2: hw02, hw01, lab01 -- penalize hw02

    assert result.points_earned.loc["A1", "hw01"] == 0
    assert result.points_earned.loc["A2", "hw02"] == 0


def test_penalize_lates_forgives_the_first_n_lates_when_order_by_is_index():
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

    gradebook.assignment_groups = {
        "homeworks": (HOMEWORK, 0.75),
        "labs": (LABS, 0.25),
    }

    result = gradelib.policies.PenalizeLates(
        within=HOMEWORK + LABS, forgive=2, order_by="index"
    )(gradebook)

    assert result.points_earned.loc["A1", "lab01"] == 0
    assert result.points_earned.loc["A2", "lab01"] == 0


def test_penalize_lates_with_empty_assignment_list_raises():
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
        gradebook.apply(gradelib.policies.PenalizeLates(within=[]))


def test_penalize_lates_by_default_takes_into_account_drops():
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
    gradebook.assignment_groups = {
        "homeworks": (gradebook.assignments.starting_with("hw"), 0.75),
        "labs": (gradebook.assignments.starting_with("lab"), 0.75),
    }

    gradebook.dropped.loc["A1", "hw02"] = True

    # after dropping, values from least to greatest
    # A1: hw02, lab02, lab01, hw01
    # A1 has all assignments late. hw01 should receive forgiveness, lab01 and lab02
    # are penalized

    result = gradebook.apply([gradelib.policies.PenalizeLates(forgive=1)])

    assert result.points_earned.loc["A1", "lab01"] == 0
    assert result.points_earned.loc["A1", "lab02"] == 0


def test_penalize_lates_adds_note_for_penalized_assignment():
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

    gradebook.assignment_groups = {"homeworks": (HOMEWORK, 1)}

    result = gradebook.apply(gradelib.policies.PenalizeLates())

    assert result.notes == {
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


def test_penalize_lates_with_forgiveness_adds_note_for_forgiven_assignments():
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

    gradebook.assignment_groups = {"homeworks": (HOMEWORK, 1)}

    result = gradebook.apply(gradelib.policies.PenalizeLates(forgive=2))

    # least to greatest value
    # A1: hw01 hw02 lab01
    # A2: hw01 hw02 lab01

    assert result.notes == {
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
