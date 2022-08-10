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
    assert isinstance(gradebook.adjustments, dict)


def as_gradebook_type(gb, gradebook_cls):
    """Creates a Gradebook object from a MutableGradebook or FinalizedGradebook."""
    return gradebook_cls(
        points_marked=gb.points_marked,
        points_possible=gb.points_possible,
        lateness=gb.lateness,
        dropped=gb.dropped,
        adjustments=gb.adjustments,
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


# points_after_adjustments
# -----------------------------------------------------------------------------


def test_points_after_adjustments_takes_deductions_into_account():
    columns = ["hw01", "hw02"]
    p1 = pd.Series(data=[10, 30], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40], index=columns, name="A2")

    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50], index=columns)

    gb = gradelib.Gradebook(points_marked, points_possible)

    gb.adjustments = {
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

    assert gb.points_after_adjustments.loc["A1", "hw01"] == 5
    assert gb.points_after_adjustments.loc["A2", "hw02"] == 40 - 15


def test_points_after_adjustments_takes_multiple_deductions_into_account():
    columns = ["hw01", "hw02"]
    p1 = pd.Series(data=[10, 30], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40], index=columns, name="A2")

    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50], index=columns)

    gb = gradelib.Gradebook(points_marked, points_possible)

    gb.adjustments = {
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

    assert gb.points_after_adjustments.loc["A1", "hw01"] == 2
    assert np.isclose(gb.points_after_adjustments.loc["A2", "hw02"], 40 - 25)


def test_points_after_adjustments_sets_floor_at_zero():
    columns = ["hw01", "hw02"]
    p1 = pd.Series(data=[10, 30], index=columns, name="A1")
    p2 = pd.Series(data=[20, 40], index=columns, name="A2")

    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([20, 50], index=columns)

    gb = gradelib.Gradebook(points_marked, points_possible)

    gb.adjustments = {
        "A1": {
            "hw01": [
                gradelib.Points(50),
            ]
        },
    }

    assert gb.points_after_adjustments.loc["A1", "hw01"] == 0


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


def test_find_student_is_case_insensitive_with_capitalized_query():
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
    s = gradebook.find_student("Justin")

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
    original.adjustments = {"A100": {"hw01": []}}

    actual = original.restricted_to_pids(ROSTER.index)

    # then
    assert actual.notes == original.notes
    assert actual.adjustments == original.adjustments


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
    original.adjustments = {"A100": {"homework 01": []}}

    actual = original.restricted_to_assignments(["homework 01", "homework 02"])

    # then
    assert actual.notes == original.notes
    assert actual.adjustments == original.adjustments


def test_restricted_to_assignments_removes_deductions_not_in_assignments():
    # when
    original = GRADESCOPE_EXAMPLE.copy()
    original.adjustments = {"A100": {"homework 01": [1], "homework 03": [3]}}

    actual = original.restricted_to_assignments(["homework 01", "homework 02"])

    # then
    assert actual.adjustments == {"A100": {"homework 01": [1]}}


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

    example_1.adjustments = {"A1": {"hw01": [1, 2, 3]}, "A2": {"hw02": [4]}}

    example_2.adjustments = {
        "A1": {"lab01": [5]},
        "A2": {"lab02": [6]},
        "A3": {"lab01": [7]},
    }

    combined = gradelib.combine_gradebooks(
        [example_1, example_2], restricted_to_pids=ROSTER.index
    )

    # then
    assert combined.adjustments == {
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


# with_assignments_combined
# -----------------------------------------------------------------------------


def test_combine_assignments():
    """test that points_marked / points_possible are added across unified assignments"""
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    # when
    result = gradebook.with_assignments_combined({"hw01": HOMEWORK_01_PARTS})

    # then
    assert len(result.assignments) == 3
    assert result.points_possible["hw01"] == 52
    assert result.points_marked.loc["A1", "hw01"] == 31

    assert result.points_possible.shape[0] == 3
    assert result.late.shape[1] == 3
    assert result.dropped.shape[1] == 3
    assert result.points_marked.shape[1] == 3


def test_combine_assignments_with_multiple_in_dictionary():
    """test that points_marked / points_possible are added across unified assignments"""
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "hw02 - testing"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")
    HOMEWORK_02_PARTS = gradebook.assignments.starting_with("hw02")

    # when
    result = gradebook.with_assignments_combined(
        {"hw01": HOMEWORK_01_PARTS, "hw02": HOMEWORK_02_PARTS}
    )

    # then
    assert len(result.assignments) == 2

    assert result.points_possible["hw01"] == 52
    assert result.points_marked.loc["A1", "hw01"] == 31

    assert result.points_possible["hw02"] == 120
    assert result.points_marked.loc["A1", "hw02"] == 110

    assert result.points_possible.shape[0] == 2
    assert result.late.shape[1] == 2
    assert result.dropped.shape[1] == 2
    assert result.points_marked.shape[1] == 2


def test_combine_assignments_with_callable():
    """test that points_marked / points_possible are added across unified assignments"""
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "hw02 - testing"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")
    HOMEWORK_02_PARTS = gradebook.assignments.starting_with("hw02")

    def assignment_to_key(s):
        return s.split("-")[0].strip()

    # when
    result = gradebook.with_assignments_combined(assignment_to_key)

    # then
    assert len(result.assignments) == 2

    assert result.points_possible["hw01"] == 52
    assert result.points_marked.loc["A1", "hw01"] == 31

    assert result.points_possible["hw02"] == 120
    assert result.points_marked.loc["A1", "hw02"] == 110

    assert result.points_possible.shape[0] == 2
    assert result.late.shape[1] == 2
    assert result.dropped.shape[1] == 2
    assert result.points_marked.shape[1] == 2


def test_combine_assignments_with_list_of_prefixes():
    """test that points_marked / points_possible are added across unified assignments"""
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "hw02 - testing", "lab 01"]
    p1 = pd.Series(data=[1, 30, 90, 20, 10], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20, 10], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20, 10], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    # when
    result = gradebook.with_assignments_combined(["hw01", "hw02"])

    # then
    assert len(result.assignments) == 3

    assert result.points_possible["hw01"] == 52
    assert result.points_marked.loc["A1", "hw01"] == 31

    assert result.points_possible["hw02"] == 120
    assert result.points_marked.loc["A1", "hw02"] == 110

    assert result.points_possible.shape[0] == 3
    assert result.late.shape[1] == 3
    assert result.dropped.shape[1] == 3
    assert result.points_marked.shape[1] == 3


def test_combine_assignments_uses_max_lateness_for_assignment_pieces():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    gradebook.lateness.loc["A1", "hw01"] = pd.Timedelta(days=3)
    gradebook.lateness.loc["A1", "hw01 - programming"] = pd.Timedelta(days=5)
    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    # when
    result = gradebook.with_assignments_combined({"hw01": HOMEWORK_01_PARTS})

    # then
    assert result.lateness.loc["A1", "hw01"] == pd.Timedelta(days=5)


def test_combine_assignments_raises_if_any_part_is_dropped():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    gradebook.dropped.loc["A1", "hw01"] = True
    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    with pytest.raises(ValueError):
        result = gradebook.with_assignments_combined({"hw01": HOMEWORK_01_PARTS})


def test_combine_assignments_combines_deductions():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    gradebook.adjustments["A1"] = {"hw01": [4], "hw01 - programming": [5]}

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    result = gradebook.with_assignments_combined({"hw01": HOMEWORK_01_PARTS})

    assert result.adjustments == {"A1": {"hw01": [4, 5]}}


def test_combine_assignments_converted_percentage_deductions_to_points():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    gradebook.adjustments["A1"] = {
        "hw01": [gradelib.Points(4)],
        "hw01 - programming": [gradelib.Percentage(0.3)],
    }

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    result = gradebook.with_assignments_combined({"hw01": HOMEWORK_01_PARTS})

    assert result.adjustments == {
        "A1": {
            "hw01": [
                gradelib.Points(4),
                gradelib.Points(15),
            ]
        }
    }


def test_combine_assignments_copies_attributes():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)
    gradebook.notes = {"A1": ["ok"]}

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    result = gradebook.with_assignments_combined({"hw01": HOMEWORK_01_PARTS})

    assert result.notes == {"A1": ["ok"]}


# with_renamed_assignments
# ------------------------


def test_with_renamed_assignments_simple_example():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)
    gradebook.notes = {"A1": ["ok"]}

    result = gradebook.with_renamed_assignments(
        {
            "hw01": "homework 01",
            "hw01 - programming": "homework 01 - programming",
        }
    )

    assert "homework 01" in result.assignments
    assert "hw01" not in result.assignments
    assert "homework 01 - programming" in result.assignments
    assert "hw01 - programming" not in result.assignments

    assert result.points_marked.loc["A1", "homework 01"] == 1

    assert_gradebook_is_sound(result)


def test_with_renamed_assignments_raises_error_on_name_clash():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)
    gradebook.notes = {"A1": ["ok"]}

    with pytest.raises(ValueError):
        gradebook.with_renamed_assignments(
            {"hw01": "hw02"},
        )


def test_with_renamed_assignments_allows_swapping_names():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)
    gradebook.notes = {"A1": ["ok"]}

    result = gradebook.with_renamed_assignments(
        {
            "hw01": "hw02",
            "hw02": "hw01",
        }
    )

    assert result.points_marked.loc["A1", "hw01"] == 90
    assert result.points_marked.loc["A1", "hw02"] == 1
    assert result.points_marked.loc["A2", "hw01"] == 15
    assert result.points_marked.loc["A2", "hw02"] == 2

    assert_gradebook_is_sound(result)


def test_with_renamed_assignments_updates_deductions():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)
    gradebook.notes = {"A1": ["ok"]}

    gradebook.adjustments = {"A1": {"hw01": [1]}}

    result = gradebook.with_renamed_assignments(
        {"hw01": "homework 01"},
    )

    assert result.adjustments == {"A1": {"homework 01": [1]}}

    assert_gradebook_is_sound(result)


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
        gradelib.Group("hw01", gradelib.Assignments(["hw01"]), weight=0.25),
        gradelib.Group("hw02", gradelib.Assignments(["hw02"]), weight=0.25),
        gradelib.Group("hw03", gradelib.Assignments(["hw03"]), weight=0.25),
        gradelib.Group("lab01", gradelib.Assignments(["lab01"]), weight=0.25),
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
        ("homeworks", ["hw01", "hw02", "hw03"], 0.5),
        ("labs", ["lab01"], 0.5),
    ]

    # then
    assert gradebook.groups == [
        gradelib.Group(
            "homeworks", gradelib.Assignments(["hw01", "hw02", "hw03"]), weight=0.5
        ),
        gradelib.Group("labs", gradelib.Assignments(["lab01"]), weight=0.5),
    ]


def test_groups_setter_allows_two_tuple_form():
    # given
    columns = ["hw01", "hw02", "hw03", "midterm"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)

    gradebook.groups = [
        ("homeworks", ["hw01", "hw02", "hw03"], 0.5),
        ("midterm", 0.5),
    ]

    # then
    assert gradebook.groups == [
        gradelib.Group(
            "homeworks", gradelib.Assignments(["hw01", "hw02", "hw03"]), weight=0.5
        ),
        gradelib.Group("midterm", gradelib.Assignments(["midterm"]), weight=0.5),
    ]


def test_groups_setter_allows_callable_for_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)

    HOMEWORKS_LAZY = lambda asmts: asmts.starting_with("hw")
    LABS_LAZY = lambda asmts: asmts.starting_with("lab")

    gradebook.groups = [
        ("homeworks", HOMEWORKS_LAZY, 0.5),
        gradelib.Group("labs", LABS_LAZY, 0.5),
    ]

    # then
    assert gradebook.groups == [
        gradelib.Group(
            "homeworks", gradelib.Assignments(["hw01", "hw02", "hw03"]), weight=0.5
        ),
        gradelib.Group("labs", gradelib.Assignments(["lab01"]), weight=0.5),
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

    gradebook.adjustments = {
        "A1": {"hw01": [gradelib.Percentage(1)]},
        "A2": {"lab01": [gradelib.Percentage(0.5)]},
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ("homeworks", HOMEWORKS, 0.5),
        gradelib.Group("labs", ["lab01"], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
        gradebook.group_effective_points_earned,
        pd.DataFrame(
            [[120, 20], [24, 10]],
            index=gradebook.students,
            columns=["homeworks", "labs"],
        ),
    )

    pd.testing.assert_frame_equal(
        gradebook.group_effective_points_possible,
        pd.DataFrame(
            [[152, 20], [152, 20]],
            index=gradebook.students,
            columns=["homeworks", "labs"],
        ),
    )


def test_group_points_respects_dropped_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A2", "hw03"] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ("homeworks", HOMEWORKS, 0.5),
        gradelib.Group("labs", ["lab01"], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
        gradebook.group_effective_points_earned,
        pd.DataFrame(
            [[91, 20], [9, 20]], index=gradebook.students, columns=["homeworks", "labs"]
        ),
    )

    pd.testing.assert_frame_equal(
        gradebook.group_effective_points_possible,
        pd.DataFrame(
            [[102, 20], [52, 20]],
            index=gradebook.students,
            columns=["homeworks", "labs"],
        ),
    )


def test_group_points_respects_deductions_and_dropped_assignments_simultaneously():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A2", "hw03"] = True
    gradebook.adjustments = {
        "A1": {"hw02": [gradelib.Points(10)], "hw03": [gradelib.Points(5)]}
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ("homeworks", HOMEWORKS, 0.5),
        gradelib.Group("labs", ["lab01"], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
        gradebook.group_effective_points_earned,
        pd.DataFrame(
            [[86, 20], [9, 20]], index=gradebook.students, columns=["homeworks", "labs"]
        ),
    )

    pd.testing.assert_frame_equal(
        gradebook.group_effective_points_possible,
        pd.DataFrame(
            [[102, 20], [52, 20]],
            index=gradebook.students,
            columns=["homeworks", "labs"],
        ),
    )


def test_group_points_raises_if_all_assignments_in_a_group_are_dropped():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc["A1", "lab01"] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ("homeworks", HOMEWORKS, 0.5),
        gradelib.Group("labs", ["lab01"], 0.5),
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
    gradebook.dropped.loc["A1", "lab01"] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ("homeworks", HOMEWORKS, 0.5),
        gradelib.Group("labs", ["lab01"], 0.5),
    ]

    # then
    with pytest.raises(ValueError):
        gradebook.group_scores


# group_scores
# -----------------------------------------------------------------------------


def test_group_scores_respects_deductions():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)

    gradebook.adjustments = {
        "A1": {"hw01": [gradelib.Percentage(1)]},
        "A2": {"lab01": [gradelib.Percentage(0.5)]},
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ("homeworks", HOMEWORKS, 0.5),
        gradelib.Group("labs", ["lab01"], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
        gradebook.group_scores,
        pd.DataFrame(
            [[120 / 152, 20 / 20], [24 / 152, 10 / 20]],
            index=gradebook.students,
            columns=["homeworks", "labs"],
        ),
    )


def test_group_scores_respects_dropped_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A2", "hw03"] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ("homeworks", HOMEWORKS, 0.5),
        gradelib.Group("labs", ["lab01"], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
        gradebook.group_scores,
        pd.DataFrame(
            [[91 / 102, 20 / 20], [9 / 52, 20 / 20]],
            index=gradebook.students,
            columns=["homeworks", "labs"],
        ),
    )


def test_group_scores_respects_deductions_and_dropped_assignments_simultaneously():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A2", "hw03"] = True
    gradebook.adjustments = {
        "A1": {"hw02": [gradelib.Points(10)], "hw03": [gradelib.Points(5)]}
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ("homeworks", HOMEWORKS, 0.5),
        gradelib.Group("labs", ["lab01"], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
        gradebook.group_scores,
        pd.DataFrame(
            [[86 / 102, 20 / 20], [9 / 52, 20 / 20]],
            index=gradebook.students,
            columns=["homeworks", "labs"],
        ),
    )


def test_group_scores_respects_normalize_assignment_weights_and_drops_and_deductions():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A2", "hw03"] = True
    gradebook.adjustments = {
        "A1": {"hw02": [gradelib.Points(10)], "hw03": [gradelib.Points(5)]}
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        gradelib.Group("homeworks", HOMEWORKS, 0.5, normalize_assignment_weights=True),
        gradelib.Group("labs", ["lab01"], 0.5),
    ]

    # then
    pd.testing.assert_frame_equal(
        gradebook.group_scores,
        pd.DataFrame(
            [
                [(1 / 2 + 0 / 50 + 85 / 100) / 2, 20 / 20],
                [(2 / 2 + 7 / 50 + 0 / 100) / 2, 20 / 20],
            ],
            index=gradebook.students,
            columns=["homeworks", "labs"],
        ),
    )


# overall_score
# -----------------------------------------------------------------------------


def test_overall_score_respects_group_weighting():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ("homeworks", HOMEWORKS, 0.6),
        gradelib.Group("labs", ["lab01"], 0.4),
    ]

    # then
    pd.testing.assert_series_equal(
        gradebook.overall_score,
        pd.Series(
            [121 / 152 * 0.6 + 20 / 20 * 0.4, 24 / 152 * 0.6 + 20 / 20 * 0.4],
            index=gradebook.students,
        ),
    )


def test_overall_score_respects_deductions():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)

    gradebook.adjustments = {
        "A1": {"hw01": [gradelib.Percentage(1)]},
        "A2": {"lab01": [gradelib.Percentage(0.5)]},
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ("homeworks", HOMEWORKS, 0.6),
        gradelib.Group("labs", ["lab01"], 0.4),
    ]

    # then
    pd.testing.assert_series_equal(
        gradebook.overall_score,
        pd.Series(
            [120 / 152 * 0.6 + 20 / 20 * 0.4, 24 / 152 * 0.6 + 10 / 20 * 0.40],
            index=gradebook.students,
        ),
    )


def test_overall_score_respects_dropped_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A2", "hw03"] = True

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ("homeworks", HOMEWORKS, 0.6),
        gradelib.Group("labs", ["lab01"], 0.4),
    ]

    # then
    pd.testing.assert_series_equal(
        gradebook.overall_score,
        pd.Series(
            [91 / 102 * 0.6 + 20 / 20 * 0.4, 9 / 52 * 0.6 + 20 / 20 * 0.40],
            index=gradebook.students,
        ),
    )


def test_overall_score_respects_deductions_and_dropped_assignments_simultaneously():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A2", "hw03"] = True
    gradebook.adjustments = {
        "A1": {"hw02": [gradelib.Points(10)], "hw03": [gradelib.Points(5)]}
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        ("homeworks", HOMEWORKS, 0.6),
        gradelib.Group("labs", ["lab01"], 0.4),
    ]

    # then
    pd.testing.assert_series_equal(
        gradebook.overall_score,
        pd.Series(
            [86 / 102 * 0.6 + 20 / 20 * 0.4, 9 / 52 * 0.6 + 20 / 20 * 0.40],
            index=gradebook.students,
        ),
    )


def test_overall_score_respects_normalize_assignment_weights_and_drops_and_deductions():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A2", "hw03"] = True
    gradebook.adjustments = {
        "A1": {"hw02": [gradelib.Points(10)], "hw03": [gradelib.Points(5)]}
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        gradelib.Group("homeworks", HOMEWORKS, 0.6, normalize_assignment_weights=True),
        gradelib.Group("labs", ["lab01"], 0.4),
    ]

    # then
    pd.testing.assert_series_equal(
        gradebook.overall_score,
        pd.Series(
            [
                (1 / 2 + 0 / 50 + 85 / 100) / 2 * 0.6 + 20 / 20 * 0.4,
                (2 / 2 + 7 / 50 + 0 / 100) / 2 * 0.6 + 20 / 20 * 0.40,
            ],
            index=gradebook.students,
        ),
    )


# letter_grades


def test_letter_grades_respects_scale():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.FinalizedGradebook(points_marked, points_possible)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A2", "hw03"] = True
    gradebook.adjustments = {
        "A1": {"hw02": [gradelib.Points(10)], "hw03": [gradelib.Points(5)]}
    }
    gradebook.scale = {
        "A+": 0.9,
        "A": 0.8,
        "A-": 0.7,
        "B+": 0.6,
        "B": 0.5,
        "B-": 0.4,
        "C+": 0.35,
        "C": 0.3,
        "C-": 0.2,
        "D": 0.1,
        "F": 0,
    }

    HOMEWORKS = gradebook.assignments.starting_with("hw")

    gradebook.groups = [
        gradelib.Group("homeworks", HOMEWORKS, 0.6, normalize_assignment_weights=True),
        gradelib.Group("labs", ["lab01"], 0.4),
    ]

    # then
    # .805 and .742
    pd.testing.assert_series_equal(
        gradebook.letter_grades, pd.Series(["A", "A-"], index=gradebook.students)
    )
