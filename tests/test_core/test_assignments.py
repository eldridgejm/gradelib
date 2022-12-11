import gradelib

# Assignments --------------------------------------------------------------------------

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



# LazyAssignments ----------------------------------------------------------------------


def test_lazy_starting_with():
    # given
    assignments = gradelib.Assignments(
        ["homework 01", "homework 02", "homework 03", "lab 01", "lab 02"]
    )
    homeworks = gradelib.LazyAssignments(lambda asmts: asmts.starting_with('home'))

    # when
    actual = homeworks(assignments)

    # then
    assert set(actual) == {"homework 01", "homework 02", "homework 03"}


def test_lazy_containing():
    # given
    homeworks = gradelib.LazyAssignments(lambda a: a.containing('work'))
    assignments = gradelib.Assignments(['homework 01', 'homework 02', 'lab 01'])

    # when
    actual = homeworks(assignments)

    # then
    assert set(actual) == {"homework 01", "homework 02"}


def test_lazy_add():
    # given
    homeworks = gradelib.LazyAssignments(lambda a: a.starting_with('hw'))
    labs = gradelib.LazyAssignments(lambda a: a.starting_with('lab'))
    assignments = gradelib.Assignments(['hw01', 'hw02', 'lab01', 'lab02', 'exam'])

    # when
    actual = (homeworks + labs)(assignments)

    # then
    assert set(actual) == {'hw01', 'hw02', 'lab01', 'lab02'}


def test_lazy_group_by():
    # given
    assignments = gradelib.Assignments(
        [
            'hw 01 - a',
            'hw 01 - b',
            'hw 02',
            "lab 01",
        ]
    )

    key = lambda s: s.split("-")[0].strip()
    grouped_hw = gradelib.LazyAssignments(lambda asmts: asmts.starting_with('hw')).group_by(key)

    # when
    actual = grouped_hw(assignments)

    # then
    actual_as_sets = {k: set(v) for k, v in actual.items()}
    assert actual_as_sets == {
        "hw 01": {"hw 01 - a", "hw 01 - b"},
        "hw 02": {"hw 02"},
    }
