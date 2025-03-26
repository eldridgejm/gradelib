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


def test_dict_form_with_extra_credit():
    group = gradelib.GradingGroup(
        {
            "homework 01": 0.5,
            "homework 02": 0.25,
            "homework 03": 0.25,
            "extra credit": gradelib.ExtraCredit(0.1),
        },
        group_weight=0.5,
    )

    assert group.assignment_weights["homework 01"] == 0.5


def test_dict_form_with_extra_credit_raises_if_regular_assignment_weights_do_not_sum_to_one():
    with raises(ValueError) as exc:
        gradelib.GradingGroup(
            {
                "homework 01": 0.5,
                "homework 02": 0.25,
                "extra credit": gradelib.ExtraCredit(0.25),
            },
            group_weight=0.5,
        )
    assert "weights must sum to one" in str(exc.value)


def test_with_extra_credit_method_creates_new_grading_group():
    # given
    group = gradelib.GradingGroup(
        {
            "homework 01": 0.5,
            "homework 02": 0.25,
            "homework 03": 0.25,
        },
        group_weight=0.5,
    )

    new_group_with_ec = group.with_extra_credit_assignments(
        {
            "extra credit": 0.1,
        }
    )

    assert new_group_with_ec.assignment_weights["homework 01"] == 0.5

    group.assignment_weights["homework 01"] = 0.6

    assert new_group_with_ec.assignment_weights["homework 01"] == 0.5
