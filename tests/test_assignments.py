import gradelib


def test_starting_with():
    # given
    assignments = gradelib.Assignments(
        ["homework 01", "homework 02", "homework 03", "lab 01", "lab 02"]
    )

    # when
    actual = assignments.starting_with("homework")

    # then
    assert set(actual) == {"homework 01", "homework 02", "homework 03"}


def test_containing():
    # given
    assignments = gradelib.Assignments(
        ["homework 01", "homework 02", "homework 03", "lab 01", "lab 02"]
    )

    # when
    actual = assignments.containing("work")

    # then
    assert set(actual) == {"homework 01", "homework 02", "homework 03"}


def test_add():
    # given
    a1 = gradelib.Assignments(["a", "b", "c"])
    a2 = gradelib.Assignments(["c", "d", "e"])

    # when
    actual = a1 + a2

    # then
    assert set(actual) == {"a", "b", "c", "d", "e"}
