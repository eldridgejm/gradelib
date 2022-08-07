import pathlib

import pytest
import pandas as pd
import numpy as np

import gradelib
import gradelib.io.ucsd
import gradelib.io.gradescope
import gradelib.io.canvas


EXAMPLES_DIRECTORY = pathlib.Path(__file__).parent / "examples"
GRADESCOPE_EXAMPLE = gradelib.io.gradescope.read(
    EXAMPLES_DIRECTORY / "gradescope.csv"
)
CANVAS_EXAMPLE = gradelib.io.canvas.read(EXAMPLES_DIRECTORY / "canvas.csv")

# the canvas example has Lab 01, which is also in Gradescope. Let's remove it
CANVAS_WITHOUT_LAB_EXAMPLE = gradelib.Gradebook(
    points_marked=CANVAS_EXAMPLE.points_marked.drop(columns="lab 01"),
    points_available=CANVAS_EXAMPLE.points_available.drop(index="lab 01"),
    lateness=CANVAS_EXAMPLE.lateness.drop(columns="lab 01"),
    dropped=CANVAS_EXAMPLE.dropped.drop(columns="lab 01"),
)

# given
ROSTER = gradelib.io.ucsd.read_egrades_roster(EXAMPLES_DIRECTORY / "egrades.csv")


def assert_gradebook_is_sound(gradebook):
    assert gradebook.points_marked.shape == gradebook.dropped.shape == gradebook.lateness.shape
    assert (gradebook.points_marked.columns == gradebook.dropped.columns).all()
    assert (gradebook.points_marked.columns == gradebook.lateness.columns).all()
    assert (gradebook.points_marked.index == gradebook.dropped.index).all()
    assert (gradebook.points_marked.index == gradebook.lateness.index).all()
    assert (gradebook.points_marked.columns == gradebook.points_available.index).all()



# assignments property
# -----------------------------------------------------------------------------


def test_assignments_are_produced_in_order():
    assert list(GRADESCOPE_EXAMPLE.assignments) == list(
        GRADESCOPE_EXAMPLE.points_marked.columns
    )


# keep_pids()
# -----------------------------------------------------------------------------


def test_keep_pids():
    # when
    actual = GRADESCOPE_EXAMPLE.keep_pids(ROSTER.index)

    # then
    assert len(actual.pids) == 3
    assert_gradebook_is_sound(actual)


def test_keep_pids_raises_if_pid_does_not_exist():
    # given
    pids = ["A12345678", "ADNEDNE00"]

    # when
    with pytest.raises(KeyError):
        actual = GRADESCOPE_EXAMPLE.keep_pids(pids)


# keep_assignments() and remove_assignments()
# -----------------------------------------------------------------------------


def test_keep_assignments():
    # when
    actual = GRADESCOPE_EXAMPLE.keep_assignments(["homework 01", "homework 02"])

    # then
    assert set(actual.assignments) == {"homework 01", "homework 02"}
    assert_gradebook_is_sound(actual)


def test_keep_assignments_raises_if_assignment_does_not_exist():
    # given
    assignments = ["homework 01", "this aint an assignment"]

    # then
    with pytest.raises(KeyError):
        GRADESCOPE_EXAMPLE.keep_assignments(assignments)


def test_remove_assignments():
    # when
    actual = GRADESCOPE_EXAMPLE.remove_assignments(
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


def test_remove_assignments_raises_if_assignment_does_not_exist():
    # given
    assignments = ["homework 01", "this aint an assignment"]

    # then
    with pytest.raises(KeyError):
        GRADESCOPE_EXAMPLE.remove_assignments(assignments)


# combine()
# -----------------------------------------------------------------------------


def test_combine_with_keep_pids():
    # when
    combined = gradelib.Gradebook.combine(
        [GRADESCOPE_EXAMPLE, CANVAS_WITHOUT_LAB_EXAMPLE], keep_pids=ROSTER.index
    )

    # then
    assert "homework 01" in combined.assignments
    assert "midterm exam" in combined.assignments
    assert_gradebook_is_sound(combined)


def test_combine_raises_if_duplicate_assignments():
    # the canvas example and the gradescope example both have lab 01.
    # when
    with pytest.raises(ValueError):
        combined = gradelib.Gradebook.combine([GRADESCOPE_EXAMPLE, CANVAS_EXAMPLE])


def test_combine_raises_if_indices_do_not_match():
    # when
    with pytest.raises(ValueError):
        combined = gradelib.Gradebook.combine(
            [CANVAS_WITHOUT_LAB_EXAMPLE, GRADESCOPE_EXAMPLE]
        )


# number_of_lates()
# -----------------------------------------------------------------------------


def test_number_of_lates():
    # when
    labs = GRADESCOPE_EXAMPLE.assignments.starting_with("lab")
    actual = GRADESCOPE_EXAMPLE.number_of_lates(within=labs)

    # then
    assert list(actual) == [1, 4, 2, 2]


def test_number_of_lates_with_empty_assignment_list_raises():
    # when
    with pytest.raises(ValueError):
        actual = GRADESCOPE_EXAMPLE.number_of_lates(within=[])


def test_number_of_lates_with_no_assignment_list_uses_all_assignments():
    # when
    actual = GRADESCOPE_EXAMPLE.number_of_lates()

    # then
    assert list(actual) == [1, 5, 2, 2]


# give_equal_weights()
# -----------------------------------------------------------------------------


def test_give_equal_weights_on_example():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)
    homeworks = gradebook.assignments.starting_with("hw")

    # when
    actual = gradebook.give_equal_weights(within=homeworks)

    # then
    assert actual.points_available.loc["hw01"] == 1
    assert actual.points_available.loc["hw02"] == 1
    assert actual.points_available.loc["hw03"] == 1
    assert actual.points_available.loc["lab01"] == 20
    assert actual.points_marked.loc["A1", "hw01"] == 1 / 2
    assert actual.points_marked.loc["A1", "hw02"] == 30 / 50


# score()
# -----------------------------------------------------------------------------


def test_score_on_simple_example():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)
    homeworks = gradebook.assignments.starting_with("hw")

    # when
    actual = gradebook.score(homeworks)

    # then
    assert np.allclose(actual.values, [121 / 152, 24 / 152], atol=1e-6)


def test_score_ignores_dropped_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)
    gradebook.dropped.loc["A1", "hw01"] = True
    gradebook.dropped.loc["A1", "hw03"] = True
    gradebook.dropped.loc["A2", "hw03"] = True
    homeworks = gradebook.assignments.starting_with("hw")

    # when
    actual = gradebook.score(homeworks)

    # then
    assert np.allclose(actual.values, [30 / 50, 9 / 52], atol=1e-6)


# total()
# -----------------------------------------------------------------------------


def test_total_on_simple_example():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)
    homeworks = gradebook.assignments.starting_with("hw")

    # when
    earned, available = gradebook.total(homeworks)

    # then
    assert np.allclose(earned.values, [121, 24], atol=1e-6)
    assert np.allclose(available.values, [152, 152], atol=1e-6)


def test_total_ignores_dropped_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)
    gradebook.dropped.loc["A1", "hw01"] = True
    gradebook.dropped.loc["A1", "hw03"] = True
    gradebook.dropped.loc["A2", "hw03"] = True
    homeworks = gradebook.assignments.starting_with("hw")

    # when
    earned, available = gradebook.total(homeworks)

    # then
    assert np.allclose(earned.values, [30, 9], atol=1e-6)
    assert np.allclose(available.values, [50, 52], atol=1e-6)


# unify_assignments()
# -----------------------------------------------------------------------------


def test_unify_assignments():
    """test that points_marked / points_available are added across unified assignments"""
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    # when
    result = gradebook.unify_assignments({"hw01": HOMEWORK_01_PARTS})

    # then
    assert len(result.assignments) == 3
    assert result.points_available["hw01"] == 52
    assert result.points_marked.loc["A1", "hw01"] == 31

    assert result.points_available.shape[0] == 3
    assert result.late.shape[1] == 3
    assert result.dropped.shape[1] == 3
    assert result.points_marked.shape[1] == 3


def test_unify_assignments_with_multiple_in_dictionary():
    """test that points_marked / points_available are added across unified assignments"""
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "hw02 - testing"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")
    HOMEWORK_02_PARTS = gradebook.assignments.starting_with("hw02")

    # when
    result = gradebook.unify_assignments(
        {"hw01": HOMEWORK_01_PARTS, "hw02": HOMEWORK_02_PARTS}
    )

    # then
    assert len(result.assignments) == 2

    assert result.points_available["hw01"] == 52
    assert result.points_marked.loc["A1", "hw01"] == 31

    assert result.points_available["hw02"] == 120
    assert result.points_marked.loc["A1", "hw02"] == 110

    assert result.points_available.shape[0] == 2
    assert result.late.shape[1] == 2
    assert result.dropped.shape[1] == 2
    assert result.points_marked.shape[1] == 2


def test_unify_assignments_with_callable():
    """test that points_marked / points_available are added across unified assignments"""
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "hw02 - testing"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")
    HOMEWORK_02_PARTS = gradebook.assignments.starting_with("hw02")

    def assignment_to_key(s):
        return s.split("-")[0].strip()

    # when
    result = gradebook.unify_assignments(assignment_to_key)

    # then
    assert len(result.assignments) == 2

    assert result.points_available["hw01"] == 52
    assert result.points_marked.loc["A1", "hw01"] == 31

    assert result.points_available["hw02"] == 120
    assert result.points_marked.loc["A1", "hw02"] == 110

    assert result.points_available.shape[0] == 2
    assert result.late.shape[1] == 2
    assert result.dropped.shape[1] == 2
    assert result.points_marked.shape[1] == 2


def test_unify_uses_max_lateness_for_assignment_pieces():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)

    gradebook.lateness.loc["A1", "hw01"] = pd.Timedelta(days=3)
    gradebook.lateness.loc["A1", "hw01 - programming"] = pd.Timedelta(days=5)
    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    # when
    result = gradebook.unify_assignments({"hw01": HOMEWORK_01_PARTS})

    # then
    assert result.lateness.loc["A1", "hw01"] == pd.Timedelta(days=5)


def test_unify_raises_if_any_part_is_dropped():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)

    gradebook.dropped.loc["A1", "hw01"] = True
    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    with pytest.raises(ValueError):
        result = gradebook.unify_assignments({"hw01": HOMEWORK_01_PARTS})


# add_assignment()
# -----------------------------------------------------------------------------


def test_add_assignment():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)

    assignment_points_marked = pd.Series([10, 20], index=["A1", "A2"])
    assignment_max = 20
    assignment_late = pd.Series([pd.Timedelta(days=2), pd.Timedelta(days=0)], index=["A1", "A2"])
    assignment_dropped = pd.Series([False, True], index=["A1", "A2"])

    # when
    result = gradebook.add_assignment(
        "new", assignment_points_marked, 20, lateness=assignment_late, dropped=assignment_dropped
    )

    # then
    assert len(result.assignments) == 5
    assert result.points_marked.loc["A1", "new"] == 10
    assert result.points_available.loc["new"] == 20


def test_add_assignment_default_none_dropped_or_late():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)

    assignment_points_marked = pd.Series([10, 20], index=["A1", "A2"])
    assignment_max = 20

    # when
    result = gradebook.add_assignment("new", assignment_points_marked, 20,)

    # then
    assert result.late.loc["A1", "new"] == False
    assert result.dropped.loc["A1", "new"] == False


def test_add_assignment_raises_on_missing_student():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)

    # A2 is missing
    assignment_points_marked = pd.Series([10], index=["A1"])
    assignment_max = 20

    # when
    with pytest.raises(ValueError):
        gradebook.add_assignment(
            "new", assignment_points_marked, 20,
        )


def test_add_assignment_raises_on_unknown_student():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)

    # foo is unknown
    assignment_points_marked = pd.Series([10, 20, 30], index=["A1", "A2", "A3"])
    assignment_max = 20

    # when
    with pytest.raises(ValueError):
        gradebook.add_assignment(
            "new", assignment_points_marked, 20,
        )


def test_add_assignment_raises_if_duplicate_name():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_marked, points_available)

    assignment_points_marked = pd.Series([10, 20], index=["A1", "A2"])
    assignment_max = 20

    # when
    with pytest.raises(ValueError):
        gradebook.add_assignment(
            "hw01", assignment_points_marked, 20,
        )


def test_lateness_fudge_defaults_to_5_minutes():
    columns = ["hw01", "hw02"]
    p1 = pd.Series(data=[1, 30], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7], index=columns, name="A2")
    l1 = pd.Series(
        data=[pd.Timedelta(seconds=30), pd.Timedelta(seconds=0)], 
        index=columns,
        name='A1'
        )
    l2 = pd.Series(
        data=[pd.Timedelta(seconds=30), pd.Timedelta(seconds=60 * 5 + 1)],
        index=columns,
        name='A2'
        )

    points_marked = pd.DataFrame([p1, p2])
    points_available = pd.Series([2, 50], index=columns)
    lateness = pd.DataFrame([l1, l2])

    gradebook = gradelib.Gradebook(points_marked, points_available, lateness)

    assert gradebook.late.loc['A1', 'hw01'] == False
    assert gradebook.late.loc['A2', 'hw02'] == True
