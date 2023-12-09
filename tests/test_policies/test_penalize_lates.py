import pytest

import pandas as pd

import gradelib
from gradelib import Points, Percentage
from gradelib.policies.lates import penalize, Deduct, Forgive


def test_with_deduct_percentage():
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

    penalize(gradebook, policy=Deduct(Percentage(1)))

    assert gradebook.points_earned.loc["A1", "lab01"] == 0
    assert gradebook.points_earned.loc["A2", "hw01"] == 0


def test_with_deduct_points():
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

    penalize(gradebook, policy=Deduct(Points(3)))

    assert gradebook.points_earned.loc["A1", "lab01"] == 17
    assert gradebook.points_earned.loc["A2", "hw01"] == 4


def test_with_custom_policy():
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

    def deduct_one_point_per_occurrence(info):
        return Points(info.number)

    penalize(gradebook, policy=deduct_one_point_per_occurrence)

    # least to most valuable:
    # A1: hw01 lab01 hw02
    # A2: hw01 hw02 lab01
    # so hw01 receives the greatest deduction

    assert gradebook.points_earned.loc["A1", "hw01"] == 27
    assert gradebook.points_earned.loc["A1", "hw02"] == 89
    assert gradebook.points_earned.loc["A1", "lab01"] == 18


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

    penalize(gradebook, policy=Deduct(Percentage(1)))

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

    penalize(gradebook, within=HOMEWORK, policy=Deduct(Percentage(1)))

    assert gradebook.points_earned.loc["A2", "hw01"] == 0


def test_forgive():
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

    penalize(gradebook, policy=Forgive(1))

    # least to greatest value
    # A1: hw01 hw02 lab01
    # A2: hw01 hw02 lab01

    assert gradebook.points_earned.loc["A1", "hw01"] == 0


def test_with_forgive_and_within():
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

    penalize(gradebook, within=HOMEWORK, policy=Forgive(2))
    penalize(gradebook, within=["lab01"], policy=Deduct(Percentage(1)))

    assert gradebook.points_earned.loc["A1", "lab01"] == 0


def test_assignments_ordered_by_value_by_default():
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

    seen = {}

    def policy(info):
        seen.setdefault(info.student, []).append(info.assignment)
        return Percentage(1)

    penalize(gradebook, within=HOMEWORK + LABS, policy=policy)

    # in order from least to most valuable
    # for AI: hw01, lab01, hw02 -- penalize hw01
    # for A2: hw02, hw01, lab01 -- penalize hw02

    assert seen["A1"] == ["hw02", "lab01", "hw01"]
    assert seen["A2"] == ["lab01", "hw01", "hw02"]


def test_order_by_index():
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

    seen = {}

    def policy(info):
        seen.setdefault(info.student, []).append(info.assignment)
        return Percentage(1)

    penalize(gradebook, within=HOMEWORK + LABS, policy=policy, order_by="index")

    # in order from least to most valuable
    # for AI: hw01, lab01, hw02 -- penalize hw01
    # for A2: hw02, hw01, lab01 -- penalize hw02

    assert seen["A1"] == ["hw01", "hw02", "lab01"]
    assert seen["A2"] == ["hw01", "hw02", "lab01"]


def test_with_callable_order_by():
    columns = ["hw01", "hw02", "lab01"]
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

    # order by the second character of the assignment name, forward
    def order_by(gradebook, student, assignments):
        return sorted(assignments, key=lambda a: a[1:])

    seen = {}

    def policy(info):
        seen.setdefault(info.student, []).append(info.assignment)
        return Percentage(1)

    penalize(gradebook, policy=policy, order_by=order_by)

    # in order from least to most valuable
    # for AI: hw01, lab01, hw02 -- penalize hw01
    # for A2: hw02, hw01, lab01 -- penalize hw02

    assert seen["A1"] == ["lab01", "hw01", "hw02"]
    assert seen["A2"] == ["hw01"]


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
        penalize(gradebook, within=[], policy=Deduct(Percentage(1)))


def test_takes_into_account_drops():
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

    penalize(gradebook, policy=Deduct(Percentage(1)))

    assert gradebook.points_earned.loc["A1", "lab01"] == 0
    assert gradebook.points_earned.loc["A1", "lab02"] == 0


def test_deduct_adds_note_for_penalized_assignment():
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

    penalize(gradebook, policy=Deduct(Percentage(1)))

    assert gradebook.notes == {
        "A1": {
            "lates": [
                "Hw02 late. Deduction: 100%. Points earned: 0.0",
                "Hw01 late. Deduction: 100%. Points earned: 0.0",
                "Hw03 late. Deduction: 100%. Points earned: 0.0",
            ]
        },
        "A2": {
            "lates": [
                "Hw01 late. Deduction: 100%. Points earned: 0.0",
            ]
        },
    }


def test_forgive_adds_note_for_forgiven_assignments():
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

    penalize(gradebook, policy=Forgive(2))

    # least to greatest value
    # A1: hw01 hw02 lab01
    # A2: hw01 hw02 lab01

    assert gradebook.notes == {
        "A1": {
            "lates": [
                "Late forgiveness #1 used on Hw02. Late forgiveness remaining: 1.",
                "Late forgiveness #2 used on Hw01. Late forgiveness remaining: 0.",
                "Hw03 late. Deduction: 100%. Points earned: 0.0",
            ]
        },
        "A2": {
            "lates": [
                "Late forgiveness #1 used on Hw01. Late forgiveness remaining: 1.",
            ]
        },
    }
