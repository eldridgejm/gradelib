import pathlib

import pandas as pd

import pytest

import gradelib
from gradelib import Percentage, Points

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

# preprocessing
# =============================================================================

# CombineAssignments()
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
    result = gradebook.apply(
        gradelib.steps.CombineAssignments({"hw01": HOMEWORK_01_PARTS})
    )

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
    result = gradebook.apply(
        gradelib.steps.CombineAssignments(
            {"hw01": HOMEWORK_01_PARTS, "hw02": HOMEWORK_02_PARTS}
        )
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
    result = gradebook.apply(gradelib.steps.CombineAssignments(assignment_to_key))

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
    result = gradebook.apply(
        gradelib.steps.CombineAssignments({"hw01": HOMEWORK_01_PARTS})
    )

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
        result = gradebook.apply(
            gradelib.steps.CombineAssignments({"hw01": HOMEWORK_01_PARTS})
        )


def test_combine_assignments_combines_deductions():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    gradebook.deductions["A1"] = {"hw01": [4], "hw01 - programming": [5]}

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    result = gradebook.apply(
        gradelib.steps.CombineAssignments({"hw01": HOMEWORK_01_PARTS})
    )

    assert result.deductions == {"A1": {"hw01": [4, 5]}}


def test_combine_assignments_converted_percentage_deductions_to_points():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible)

    gradebook.deductions["A1"] = {
        "hw01": [gradelib.Points(4)],
        "hw01 - programming": [gradelib.Percentage(0.3)],
    }

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    result = gradebook.apply(
        gradelib.steps.CombineAssignments({"hw01": HOMEWORK_01_PARTS})
    )

    assert result.deductions == {
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

    result = gradebook.apply(
        gradelib.steps.CombineAssignments({"hw01": HOMEWORK_01_PARTS})
    )

    assert result.notes == {"A1": ["ok"]}



# PenalizeLates()
# -----------------------------------------------------------------------------

def _number_of_lates(gb, within):
    return gb.late[within].sum(axis=1)

def test_penalize_lates_without_forgiveness_or_within_penalizes_all_lates():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame([
            pd.to_timedelta([0, 0, 5000], 's'),
            pd.to_timedelta([6000, 0, 0], 's')
        ], columns=columns, index=points_marked.index)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    result = gradebook.apply(
        gradelib.steps.PenalizeLates()
    )

    assert result.deductions == {
            "A1": {"lab01": [Percentage(1)]},
            "A2": {"hw01": [Percentage(1)]},
    }

def test_penalize_lates_with_custom_penalty():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame([
            pd.to_timedelta([0, 0, 5000], 's'),
            pd.to_timedelta([6000, 0, 0], 's')
        ], columns=columns, index=points_marked.index)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    result = gradebook.apply(
        gradelib.steps.PenalizeLates(deduction=Points(3))
    )

    assert result.deductions == {
            "A1": {"lab01": [Points(3)]},
            "A2": {"hw01": [Points(3)]},
    }

def test_penalize_lates_within_assignments():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame([
            pd.to_timedelta([0, 0, 5000], 's'),
            pd.to_timedelta([6000, 0, 0], 's')
        ], columns=columns, index=points_marked.index)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    result = gradebook.apply(
        gradelib.steps.PenalizeLates(within=HOMEWORK)
    )

    assert result.deductions == {
            "A2": {"hw01": [Percentage(1)]},
    }

def test_penalize_lates_within_accepts_callable():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame([
            pd.to_timedelta([0, 0, 5000], 's'),
            pd.to_timedelta([6000, 0, 0], 's')
        ], columns=columns, index=points_marked.index)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible, lateness=lateness)

    HOMEWORK = lambda asmts: asmts.starting_with("hw")

    result = gradebook.apply(
        gradelib.steps.PenalizeLates(within=HOMEWORK)
    )

    assert result.deductions == {
            "A2": {"hw01": [Percentage(1)]},
    }

def test_penalize_lates_with_forgiveness():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame([
            pd.to_timedelta([5000, 0, 5000], 's'),
            pd.to_timedelta([6000, 0, 0], 's')
        ], columns=columns, index=points_marked.index)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    result = gradebook.apply(
        gradelib.steps.PenalizeLates(forgive=1)
    )

    assert result.deductions == {
            "A1": {"lab01": [Percentage(1)]},
    }

def test_penalize_lates_with_forgiveness_and_within():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame([
            pd.to_timedelta([5000, 0, 5000], 's'),
            pd.to_timedelta([6000, 0, 0], 's')
        ], columns=columns, index=points_marked.index)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    result = gradebook.apply([
        gradelib.steps.PenalizeLates(within=HOMEWORK, forgive=2),
        gradelib.steps.PenalizeLates(within=['lab01'])
    ])

    assert result.deductions == {
            "A1": {"lab01": [Percentage(1)]},
    }

def test_penalize_lates_forgives_the_first_n_lates():
    # by "first", we mean in the order specified by the `within` argument
    # student A10000000 had late lab 01, 02, 03, and 07

    assignments = ["lab 02", "lab 07", "lab 01", "lab 03"]

    # when
    actual = GRADESCOPE_EXAMPLE.apply(gradelib.steps.PenalizeLates(forgive=2, within=assignments))

    # then
    assert actual.deductions['A10000000'] == {
        "lab 01": [Percentage(1)],
        "lab 03": [Percentage(1)],
    }


def test_penalize_lates_with_empty_assignment_list_raises():
    # when
    with pytest.raises(ValueError):
        actual = GRADESCOPE_EXAMPLE.apply(gradelib.steps.PenalizeLates(within=[]))


def test_penalize_lates_does_not_forgive_dropped():
    # given
    labs = GRADESCOPE_EXAMPLE.assignments.starting_with("lab")
    dropped = GRADESCOPE_EXAMPLE.dropped.copy()
    dropped.iloc[:, :] = True
    example = gradelib.MutableGradebook(
        points_marked=GRADESCOPE_EXAMPLE.points_marked,
        points_possible=GRADESCOPE_EXAMPLE.points_possible,
        lateness=GRADESCOPE_EXAMPLE.lateness,
        dropped=dropped,
    ).copy()

    # when
    actual = example.apply(gradelib.steps.PenalizeLates(forgive=3, within=labs))

    # then
    assert list(_number_of_lates(actual, within=labs)) == [1, 4, 2, 2]
    assert_gradebook_is_sound(actual)


