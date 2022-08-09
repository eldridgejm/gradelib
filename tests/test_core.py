import pathlib

import pytest
import pandas as pd
import numpy as np

import gradelib
import gradelib.io.ucsd
import gradelib.io.gradescope
import gradelib.io.canvas


EXAMPLES_DIRECTORY = pathlib.Path(__file__).parent / "examples"
GRADESCOPE_EXAMPLE = gradelib.io.gradescope.read(EXAMPLES_DIRECTORY / "gradescope.csv")
CANVAS_EXAMPLE = gradelib.io.canvas.read(EXAMPLES_DIRECTORY / "canvas.csv")

# the canvas example has Lab 01, which is also in Gradescope. Let's remove it
CANVAS_WITHOUT_LAB_EXAMPLE = gradelib.MutableGradebook(
    points_marked=CANVAS_EXAMPLE.points_marked.drop(columns="lab 01"),
    points_possible=CANVAS_EXAMPLE.points_possible.drop(index="lab 01"),
    lateness=CANVAS_EXAMPLE.lateness.drop(columns="lab 01"),
    dropped=CANVAS_EXAMPLE.dropped.drop(columns="lab 01"),
)

# given
ROSTER = gradelib.io.ucsd.read_egrades_roster(EXAMPLES_DIRECTORY / "egrades.csv")


def assert_gradebook_is_sound(gradebook):
    assert (
        gradebook.points_marked.shape
        == gradebook.dropped.shape
        == gradebook.lateness.shape
    )
    assert (gradebook.points_marked.columns == gradebook.dropped.columns).all()
    assert (gradebook.points_marked.columns == gradebook.lateness.columns).all()
    assert (gradebook.points_marked.index == gradebook.dropped.index).all()
    assert (gradebook.points_marked.index == gradebook.lateness.index).all()
    assert (gradebook.points_marked.columns == gradebook.points_possible.index).all()
    assert isinstance(gradebook.deductions, dict)


def as_gradebook_type(gb, gradebook_cls):
    """Creates a Gradebook object from a MutableGradebook or FinalizedGradebook."""
    return gradebook_cls(
        points_marked=gb.points_marked,
        points_possible=gb.points_possible,
        lateness=gb.lateness,
        dropped=gb.dropped,
        deductions=gb.deductions,
        notes=gb.notes,
        opts=gb.opts,
    )


# assignments property
# -----------------------------------------------------------------------------


def test_assignments_are_produced_in_order():
    assert list(GRADESCOPE_EXAMPLE.assignments) == list(
        GRADESCOPE_EXAMPLE.points_marked.columns
    )


# Gradebook
# =============================================================================

# lateness fudge
# -----------------------------------------------------------------------------


def test_lateness_fudge_defaults_to_5_minutes():
    columns = ["hw01", "hw02"]
    p1 = pd.Series(data=[1, 30], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7], index=columns, name="A2")
    l1 = pd.Series(
        data=[pd.Timedelta(seconds=30), pd.Timedelta(seconds=0)],
        index=columns,
        name="A1",
    )
    l2 = pd.Series(
        data=[pd.Timedelta(seconds=30), pd.Timedelta(seconds=60 * 5 + 1)],
        index=columns,
        name="A2",
    )

    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50], index=columns)
    lateness = pd.DataFrame([l1, l2])

    gradebook = gradelib.Gradebook(points_marked, points_possible, lateness)

    assert gradebook.late.loc["A1", "hw01"] == False
    assert gradebook.late.loc["A2", "hw02"] == True


def test_lateness_fudge_can_be_changed():
    columns = ["hw01", "hw02"]
    p1 = pd.Series(data=[1, 30], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7], index=columns, name="A2")
    l1 = pd.Series(
        data=[pd.Timedelta(seconds=30), pd.Timedelta(seconds=0)],
        index=columns,
        name="A1",
    )
    l2 = pd.Series(
        data=[pd.Timedelta(seconds=30), pd.Timedelta(seconds=60 * 5 + 1)],
        index=columns,
        name="A2",
    )

    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50], index=columns)
    lateness = pd.DataFrame([l1, l2])

    gradebook = gradelib.Gradebook(points_marked, points_possible, lateness)

    assert gradebook.late.loc["A1", "hw01"] == False
    assert gradebook.late.loc["A2", "hw02"] == True

    gradebook.opts.lateness_fudge = 10

    assert gradebook.late.loc["A1", "hw01"] == True
    assert gradebook.late.loc["A2", "hw02"] == True


# points_after_deductions
# -----------------------------------------------------------------------------


def test_points_after_deductions_takes_deductions_into_account():
    columns = ["hw01", "hw02"]
    p1 = pd.Series(data=[10, 30], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40], index=columns, name="A2")

    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50], index=columns)

    gb = gradelib.Gradebook(points_marked, points_possible)

    gb.deductions = {
        "A1": {
            "hw01": [
                gradelib.Points(5),
            ]
        },
        "A2": {
            "hw02": [
                gradelib.Percentage(0.3),
            ]
        },
    }

    assert gb.points_after_deductions.loc["A1", "hw01"] == 5
    assert gb.points_after_deductions.loc["A2", "hw02"] == 40 - 15


def test_points_after_deductions_takes_multiple_deductions_into_account():
    columns = ["hw01", "hw02"]
    p1 = pd.Series(data=[10, 30], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40], index=columns, name="A2")

    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50], index=columns)

    gb = gradelib.Gradebook(points_marked, points_possible)

    gb.deductions = {
        "A1": {
            "hw01": [
                gradelib.Points(5),
                gradelib.Points(3),
            ]
        },
        "A2": {
            "hw02": [
                gradelib.Percentage(0.3),
                gradelib.Percentage(0.2),
            ]
        },
    }

    assert gb.points_after_deductions.loc["A1", "hw01"] == 2
    assert np.isclose(gb.points_after_deductions.loc["A2", "hw02"], 40 - 25)


def test_points_after_deductions_sets_floor_at_zero():
    columns = ["hw01", "hw02"]
    p1 = pd.Series(data=[10, 30], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40], index=columns, name="A2")

    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50], index=columns)

    gb = gradelib.Gradebook(points_marked, points_possible)

    gb.deductions = {
        "A1": {
            "hw01": [
                gradelib.Points(50),
            ]
        },
    }

    assert gb.points_after_deductions.loc["A1", "hw01"] == 0


# give_equal_weights()
# -----------------------------------------------------------------------------


def test_give_equal_weights_on_example():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)
    homeworks = gradebook.assignments.starting_with("hw")

    # when
    actual = gradebook.give_equal_weights(within=homeworks)

    # then
    assert actual.points_possible.loc["hw01"] == 1
    assert actual.points_possible.loc["hw02"] == 1
    assert actual.points_possible.loc["hw03"] == 1
    assert actual.points_possible.loc["lab01"] == 20
    assert actual.points_marked.loc["A1", "hw01"] == 1 / 2
    assert actual.points_marked.loc["A1", "hw02"] == 30 / 50


# find_student()
# -----------------------------------------------------------------------------


def test_find_student_is_case_insensitive():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    points_marked.index = [
        gradelib.Student("A1", "Justin Eldridge"),
        gradelib.Student("A2", "Barack Obama"),
    ]
    gradebook = gradelib.Gradebook(points_marked, points_possible)

    # when
    s = gradebook.find_student("justin")

    # then
    assert s == points_marked.index[0]


def test_find_student_raises_on_multiple_matches():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    points_marked.index = [
        gradelib.Student("A1", "Justin Eldridge"),
        gradelib.Student("A2", "Justin Other"),
    ]
    gradebook = gradelib.Gradebook(points_marked, points_possible)

    # when
    with pytest.raises(ValueError):
        gradebook.find_student("justin")


def test_find_student_raises_on_no_match():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    points_marked.index = [
        gradelib.Student("A1", "Justin Eldridge"),
        gradelib.Student("A2", "Justin Other"),
    ]
    gradebook = gradelib.Gradebook(points_marked, points_possible)

    # when
    with pytest.raises(ValueError):
        gradebook.find_student("steve")


# MutableGradebook
# =============================================================================


# restricted_to_pids()
# -----------------------------------------------------------------------------


def test_restricted_to_pids():
    # when
    actual = GRADESCOPE_EXAMPLE.restricted_to_pids(ROSTER.index)

    # then
    assert len(actual.pids) == 3
    assert_gradebook_is_sound(actual)


def test_restricted_to_pids_raises_if_pid_does_not_exist():
    # given
    pids = ["A12345678", "ADNEDNE00"]

    # when
    with pytest.raises(KeyError):
        actual = GRADESCOPE_EXAMPLE.restricted_to_pids(pids)


def test_restricted_to_pids_copies_all_attributes():
    # when
    original = GRADESCOPE_EXAMPLE.copy()
    original.notes = {"A100": {"drop": ["testing this"]}}
    original.deductions = {"A100": {"hw01": []}}

    actual = original.restricted_to_pids(ROSTER.index)

    # then
    assert actual.notes == original.notes
    assert actual.deductions == original.deductions


# restricted_to_assignments() and without_assignments()
# -----------------------------------------------------------------------------


def test_restricted_to_assignments():
    # when
    actual = GRADESCOPE_EXAMPLE.restricted_to_assignments(
        ["homework 01", "homework 02"]
    )

    # then
    assert set(actual.assignments) == {"homework 01", "homework 02"}
    assert_gradebook_is_sound(actual)


def test_restricted_to_assignments_raises_if_assignment_does_not_exist():
    # given
    assignments = ["homework 01", "this aint an assignment"]

    # then
    with pytest.raises(KeyError):
        GRADESCOPE_EXAMPLE.restricted_to_assignments(assignments)


def test_restricted_to_assignments_copies_all_attributes():
    # when
    original = GRADESCOPE_EXAMPLE.copy()
    original.notes = {"A100": {"drop": ["testing this"]}}
    original.deductions = {"A100": {"homework 01": []}}

    actual = original.restricted_to_assignments(["homework 01", "homework 02"])

    # then
    assert actual.notes == original.notes
    assert actual.deductions == original.deductions


def test_restricted_to_assignments_removes_deductions_not_in_assignments():
    # when
    original = GRADESCOPE_EXAMPLE.copy()
    original.deductions = {"A100": {"homework 01": [1], "homework 03": [3]}}

    actual = original.restricted_to_assignments(["homework 01", "homework 02"])

    # then
    assert actual.deductions == {"A100": {"homework 01": [1]}}


def test_without_assignments():
    # when
    actual = GRADESCOPE_EXAMPLE.without_assignments(
        GRADESCOPE_EXAMPLE.assignments.starting_with("lab")
    )

    # then
    assert set(actual.assignments) == {
        "homework 01",
        "homework 02",
        "homework 03",
        "homework 04",
        "homework 05",
        "homework 06",
        "homework 07",
        "project 01",
        "project 02",
    }
    assert_gradebook_is_sound(actual)


def test_without_assignments_raises_if_assignment_does_not_exist():
    # given
    assignments = ["homework 01", "this aint an assignment"]

    # then
    with pytest.raises(KeyError):
        GRADESCOPE_EXAMPLE.without_assignments(assignments)


# combine_gradebooks()
# -----------------------------------------------------------------------------


def test_combine_gradebooks_with_restricted_to_pids():
    # when
    combined = gradelib.combine_gradebooks(
        [GRADESCOPE_EXAMPLE, CANVAS_WITHOUT_LAB_EXAMPLE],
        restricted_to_pids=ROSTER.index,
    )

    # then
    assert "homework 01" in combined.assignments
    assert "midterm exam" in combined.assignments
    assert_gradebook_is_sound(combined)


def test_combine_gradebooks_raises_if_duplicate_assignments():
    # the canvas example and the gradescope example both have lab 01.
    # when
    with pytest.raises(ValueError):
        combined = gradelib.combine_gradebooks([GRADESCOPE_EXAMPLE, CANVAS_EXAMPLE])


def test_combine_gradebooks_raises_if_indices_do_not_match():
    # when
    with pytest.raises(ValueError):
        combined = gradelib.combine_gradebooks(
            [CANVAS_WITHOUT_LAB_EXAMPLE, GRADESCOPE_EXAMPLE]
        )


def test_combine_gradebooks_concatenates_deductions():
    # when
    example_1 = GRADESCOPE_EXAMPLE.copy()
    example_2 = CANVAS_WITHOUT_LAB_EXAMPLE.copy()

    example_1.deductions = {"A1": {"hw01": [1, 2, 3]}, "A2": {"hw02": [4]}}

    example_2.deductions = {
        "A1": {"lab01": [5]},
        "A2": {"lab02": [6]},
        "A3": {"lab01": [7]},
    }

    combined = gradelib.combine_gradebooks(
        [example_1, example_2], restricted_to_pids=ROSTER.index
    )

    # then
    assert combined.deductions == {
        "A1": {"hw01": [1, 2, 3], "lab01": [5]},
        "A2": {"hw02": [4], "lab02": [6]},
        "A3": {"lab01": [7]},
    }


def test_combine_gradebooks_concatenates_notes():
    # when
    example_1 = GRADESCOPE_EXAMPLE.copy()
    example_2 = CANVAS_WITHOUT_LAB_EXAMPLE.copy()

    example_1.notes = {"A1": {"drop": ["foo", "bar"]}, "A2": {"misc": ["baz"]}}

    example_2.notes = {
        "A1": {"drop": ["baz", "quux"]},
        "A2": {"late": ["ok"]},
        "A3": {"late": ["message"]},
    }

    combined = gradelib.combine_gradebooks(
        [example_1, example_2], restricted_to_pids=ROSTER.index
    )

    # then
    assert combined.notes == {
        "A1": {"drop": ["foo", "bar", "baz", "quux"]},
        "A2": {"misc": ["baz"], "late": ["ok"]},
        "A3": {"late": ["message"]},
    }


# with_assignment()
# -----------------------------------------------------------------------------


def test_with_assignment():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    assignment_points_marked = pd.Series([10, 20], index=["A1", "A2"])
    assignment_max = 20
    assignment_late = pd.Series(
        [pd.Timedelta(days=2), pd.Timedelta(days=0)], index=["A1", "A2"]
    )
    assignment_dropped = pd.Series([False, True], index=["A1", "A2"])

    # when
    result = gradebook.with_assignment(
        "new",
        assignment_points_marked,
        points_possible=20,
        lateness=assignment_late,
        dropped=assignment_dropped,
    )

    # then
    assert len(result.assignments) == 5
    assert result.points_marked.loc["A1", "new"] == 10
    assert result.points_possible.loc["new"] == 20
    assert isinstance(result.lateness.index[0], gradelib.Student)
    assert isinstance(result.dropped.index[0], gradelib.Student)


def test_with_assignment_default_none_dropped_or_late():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    assignment_points_marked = pd.Series([10, 20], index=["A1", "A2"])
    assignment_max = 20

    # when
    result = gradebook.with_assignment(
        "new",
        assignment_points_marked,
        20,
    )

    # then
    assert result.late.loc["A1", "new"] == False
    assert result.dropped.loc["A1", "new"] == False


def test_with_assignment_raises_on_missing_student():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    # A2 is missing
    assignment_points_marked = pd.Series([10], index=["A1"])
    assignment_max = 20

    # when
    with pytest.raises(ValueError):
        gradebook.with_assignment(
            "new",
            assignment_points_marked,
            20,
        )


def test_with_assignment_raises_on_unknown_student():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    # foo is unknown
    assignment_points_marked = pd.Series([10, 20, 30], index=["A1", "A2", "A3"])
    assignment_max = 20

    # when
    with pytest.raises(ValueError):
        gradebook.with_assignment(
            "new",
            assignment_points_marked,
            20,
        )


def test_with_assignment_raises_if_duplicate_name():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    assignment_points_marked = pd.Series([10, 20], index=["A1", "A2"])

    # when
    with pytest.raises(ValueError):
        gradebook.with_assignment(
            "hw01",
            assignment_points_marked,
            20,
        )


# FinalizedGradebook
# ==================

# default_groups

def test_default_groups_one_assignment_per_group_equally_weighted():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)

    # then
    assert gradebook.default_groups == [
            gradelib.Group('hw01', gradelib.Assignments(['hw01']), weight=.25),
            gradelib.Group('hw02', gradelib.Assignments(['hw02']), weight=.25),
            gradelib.Group('hw03', gradelib.Assignments(['hw03']), weight=.25),
            gradelib.Group('lab01', gradelib.Assignments(['lab01']), weight=.25),
    ]

# groups

def test_groups_setter_allows_three_tuple_form():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)

    gradebook.groups = [
        ('homeworks', ['hw01', 'hw02', 'hw03'], 0.5),
        ('labs', ['lab01'], 0.5),
    ]

    # then
    assert gradebook.groups == [
            gradelib.Group('homeworks', gradelib.Assignments(['hw01', 'hw02', 'hw03']), weight=.5),
            gradelib.Group('labs', gradelib.Assignments(['lab01']), weight=.5),
    ]

def test_groups_setter_allows_callable_for_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)

    HOMEWORKS_LAZY = lambda asmts: asmts.starting_with('hw')
    LABS_LAZY = lambda asmts: asmts.starting_with('lab')

    gradebook.groups = [
        ('homeworks', HOMEWORKS_LAZY, 0.5),
        gradelib.Group('labs', LABS_LAZY, 0.5),
    ]

    # then
    assert gradebook.groups == [
            gradelib.Group('homeworks', gradelib.Assignments(['hw01', 'hw02', 'hw03']), weight=.5),
            gradelib.Group('labs', gradelib.Assignments(['lab01']), weight=.5),
    ]

# .group_effective_points
# -----------------------

def test_group_points_respects_deductions():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)

    gradebook.deductions = {
        'A1': {'hw01': [gradelib.Percentage(1)]},
        'A2': {'lab01': [gradelib.Percentage(.5)]},
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ('homeworks', HOMEWORKS, 0.5),
        gradelib.Group('labs', ['lab01'], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
            gradebook.group_effective_points_earned,
            pd.DataFrame([
                [120, 20],
                [24, 10]
                ], index=gradebook.students, columns=['homeworks', 'labs'])
            )

    pd.testing.assert_frame_equal(
            gradebook.group_effective_points_possible,
            pd.DataFrame([
                [152, 20],
                [152, 20]
                ], index=gradebook.students, columns=['homeworks', 'labs'])
            )

def test_group_points_respects_dropped_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc['A1', 'hw02'] = True
    gradebook.dropped.loc['A2', 'hw03'] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ('homeworks', HOMEWORKS, 0.5),
        gradelib.Group('labs', ['lab01'], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
            gradebook.group_effective_points_earned,
            pd.DataFrame([
                [91, 20],
                [9, 20]
                ], index=gradebook.students, columns=['homeworks', 'labs'])
            )

    pd.testing.assert_frame_equal(
            gradebook.group_effective_points_possible,
            pd.DataFrame([
                [102, 20],
                [52, 20]
                ], index=gradebook.students, columns=['homeworks', 'labs'])
            )

def test_group_points_respects_deductions_and_dropped_assignments_simultaneously():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc['A1', 'hw02'] = True
    gradebook.dropped.loc['A2', 'hw03'] = True
    gradebook.deductions = {
            "A1": {"hw02": [gradelib.Points(10)], "hw03": [gradelib.Points(5)]}
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ('homeworks', HOMEWORKS, 0.5),
        gradelib.Group('labs', ['lab01'], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
            gradebook.group_effective_points_earned,
            pd.DataFrame([
                [86, 20],
                [9, 20]
                ], index=gradebook.students, columns=['homeworks', 'labs'])
            )

    pd.testing.assert_frame_equal(
            gradebook.group_effective_points_possible,
            pd.DataFrame([
                [102, 20],
                [52, 20]
                ], index=gradebook.students, columns=['homeworks', 'labs'])
            )

def test_group_points_raises_if_all_assignments_in_a_group_are_dropped():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc['A1', 'lab01'] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ('homeworks', HOMEWORKS, 0.5),
        gradelib.Group('labs', ['lab01'], 0.5),
    ]

    # then
    with pytest.raises(ValueError):
        gradebook.group_effective_points_possible


# group_scores
# ------------

def test_group_scores_raises_if_all_assignments_in_a_group_are_dropped():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc['A1', 'lab01'] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ('homeworks', HOMEWORKS, 0.5),
        gradelib.Group('labs', ['lab01'], 0.5),
    ]

    # then
    with pytest.raises(ValueError):
        gradebook.group_scores

# group_scores()
# -----------------------------------------------------------------------------

def test_group_scores_respects_deductions():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)

    gradebook.deductions = {
        'A1': {'hw01': [gradelib.Percentage(1)]},
        'A2': {'lab01': [gradelib.Percentage(.5)]},
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ('homeworks', HOMEWORKS, 0.5),
        gradelib.Group('labs', ['lab01'], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
            gradebook.group_scores,
            pd.DataFrame([
                [120/152, 20/20],
                [24/152, 10/20]
                ], index=gradebook.students, columns=['homeworks', 'labs'])
            )


def test_group_scores_respects_dropped_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc['A1', 'hw02'] = True
    gradebook.dropped.loc['A2', 'hw03'] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ('homeworks', HOMEWORKS, 0.5),
        gradelib.Group('labs', ['lab01'], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
            gradebook.group_scores,
            pd.DataFrame([
                [91/102, 20/20],
                [9/52, 20/20]
                ], index=gradebook.students, columns=['homeworks', 'labs'])
            )

def test_group_scores_respects_deductions_and_dropped_assignments_simultaneously():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc['A1', 'hw02'] = True
    gradebook.dropped.loc['A2', 'hw03'] = True
    gradebook.deductions = {
            "A1": {"hw02": [gradelib.Points(10)], "hw03": [gradelib.Points(5)]}
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ('homeworks', HOMEWORKS, 0.5),
        gradelib.Group('labs', ['lab01'], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
            gradebook.group_scores,
            pd.DataFrame([
                [86/102, 20/20],
                [9/52, 20/20]
                ], index=gradebook.students, columns=['homeworks', 'labs'])
            )

def test_group_scores_respects_normalize_assignment_weights_and_drops_and_deductions():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc['A1', 'hw02'] = True
    gradebook.dropped.loc['A2', 'hw03'] = True
    gradebook.deductions = {
            "A1": {"hw02": [gradelib.Points(10)], "hw03": [gradelib.Points(5)]}
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        gradelib.Group('homeworks', HOMEWORKS, 0.5, normalize_assignment_weights=True),
        gradelib.Group('labs', ['lab01'], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
            gradebook.group_scores,
            pd.DataFrame([
                [(1/2 + 0/50 + 85/100)/2, 20/20],
                [(2/2 + 7/50 + 0/100)/2, 20/20]
                ], index=gradebook.students, columns=['homeworks', 'labs'])
            )
