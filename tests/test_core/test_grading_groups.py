import gradelib

from pytest import raises  # pyright: ignore


def test_verifies_that_assignment_weights_add_to_one():
    with raises(ValueError):
        gradelib.GradingGroup({"foo": 0.2, "bar": 0.5, "baz": 0.1}, group_weight=0.5)


def test_verifies_that_assignment_weights_are_between_0_and_1():
    with raises(ValueError):
        gradelib.GradingGroup({"foo": -0.5, "bar": 1.5}, group_weight=0.5)


def test_verifies_that_group_weight_is_between_0_and_1():
    with raises(ValueError):
        gradelib.GradingGroup({"foo": 0.5, "bar": 0.5}, group_weight=42.0)


def test_with_equal_weights():
    group = gradelib.GradingGroup.with_equal_weights(["foo", "bar"], group_weight=0.5)
    assert group.assignment_weights == {"foo": 0.5, "bar": 0.5}
    assert group.group_weight == 0.5


def test_with_proportional_weights():
    # create a dummy gradebook for testing with different points possible
    import pandas as pd

    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[10, 10, 10], index=columns, name="A1")
    points_earned = pd.DataFrame([p1])
    points_possible = pd.Series([25, 75, 50], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    # test with just the homework assignments
    homework_assignments = ["hw01", "hw02"]
    group = gradelib.GradingGroup.with_proportional_weights(
        gradebook, homework_assignments, group_weight=0.75
    )

    # assignment weights should be proportional to points possible
    assert group.assignment_weights["hw01"] == 25 / 100  # 25 points out of 100 total
    assert group.assignment_weights["hw02"] == 75 / 100  # 75 points out of 100 total
    assert group.group_weight == 0.75

    # weights should sum to 1
    assert sum(group.assignment_weights.values()) == 1.0
