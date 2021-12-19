import gradelib


def test_getitem_with_predicate():
    # given
    assignments = gradelib.Assignments(
        ["homework 01", "homework 02", "homework 03", "lab 01", "lab 02"]
    )

    def predicate(s):
        return s.startswith('home')

    # when
    actual = assignments[predicate]

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


def test_group_by():
    # given
    assignments = gradelib.Assignments(
        [
            "homework 01",
            "homework 01 - programming",
            "homework 02",
            "homework 03",
            "homework 03 - programming",
            "lab 01",
            "lab 02",
        ]
    )

    # when
    actual = assignments.group_by(lambda s: s.split("-")[0].strip())

    # then
    actual_as_sets = {k: set(v) for k, v in actual.items()}
    assert actual_as_sets == {
        "homework 01": {"homework 01", "homework 01 - programming"},
        "homework 02": {"homework 02"},
        "homework 03": {"homework 03", "homework 03 - programming"},
        "lab 01": {"lab 01"},
        "lab 02": {"lab 02"},
    }
    assert isinstance(actual["homework 01"], gradelib.Assignments)
