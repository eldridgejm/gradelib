import pytest  # pyright: ignore

import gradelib

# find_student -------------------------------------------------------------------------


def test_find_student_is_case_insensitive():
    # given
    students = gradelib.Students(
        [
            gradelib.Student("A1", "Justin"),
            gradelib.Student("A2", "tyler"),
            gradelib.Student("A3", "tyrant"),
        ]
    )

    # when
    s = students.find("justin")

    # then
    assert s == gradelib.Student("A1", "justin")


def test_find_student_is_case_insensitive_with_capitalized_query():
    # given
    students = gradelib.Students(
        [
            gradelib.Student("a1", "justin"),
            gradelib.Student("a2", "tyler"),
            gradelib.Student("a3", "tyrant"),
        ]
    )

    # when
    s = students.find("justin")

    # then
    assert s == gradelib.Student("a1", "justin")


def test_find_student_raises_on_multiple_matches():
    # given
    students = gradelib.Students(
        [
            gradelib.Student("a1", "justin"),
            gradelib.Student("a2", "tyler"),
            gradelib.Student("a3", "tyrant"),
        ]
    )

    # when/then
    with pytest.raises(ValueError):
        students.find("ty")


def test_find_student_raises_on_no_match():
    # given
    students = gradelib.Students(
        [
            gradelib.Student("a1", "justin"),
            gradelib.Student("a2", "tyler"),
            gradelib.Student("a3", "tyrant"),
        ]
    )

    # when/then
    with pytest.raises(ValueError):
        students.find("zzz")
