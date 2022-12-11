import gradelib

from pytest import raises


def test_verifies_that_assignment_weights_add_to_one():
    with raises(ValueError):
        gradelib.AssignmentGroup({'foo': .2, 'bar': .5, 'baz': .1}, group_weight=0.5)

def test_verifies_that_assignment_weights_are_between_0_and_1():
    with raises(ValueError):
        gradelib.AssignmentGroup({'foo': -.5, 'bar': 1.5}, group_weight=0.5)


def test_verifies_that_group_weight_is_between_0_and_1():
    with raises(ValueError):
        gradelib.AssignmentGroup({'foo': .5, 'bar': 0.5}, group_weight=42.0)
