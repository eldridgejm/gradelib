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

def test_penalize_lates_with_custom_flat_deduction():
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

def test_penalize_lates_with_callable_deduction():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame([
            pd.to_timedelta([6000, 6000, 6000], 's'),
            pd.to_timedelta([0, 0, 0], 's')
        ], columns=columns, index=points_marked.index)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradebook.opts.lateness_fudge = 60 * 5

    def deduction(info):
        return Points(info.number)

    result = gradebook.apply(
        gradelib.steps.PenalizeLates(deduction=deduction)
    )

    assert result.deductions == {
            "A1": {
                "hw01": [Points(1)],
                "hw02": [Points(2)],
                "lab01": [Points(3)]
            },
    }

def test_penalize_lates_with_callable_deduction_does_not_count_forgiven():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame([
            pd.to_timedelta([6000, 6000, 6000], 's'),
            pd.to_timedelta([0, 0, 0], 's')
        ], columns=columns, index=points_marked.index)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradebook.opts.lateness_fudge = 60 * 5

    def deduction(info):
        return Points(info.number)

    result = gradebook.apply(
        gradelib.steps.PenalizeLates(deduction=deduction, forgive=1)
    )

    assert result.deductions == {
            "A1": {
                "hw02": [Points(1)],
                "lab01": [Points(2)]
            },
    }

def test_penalize_lates_respects_lateness_fudge():
    # given
    columns = ["hw01", "hw02", "lab01"]
    p1 = pd.Series(data=[30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[7, 15, 20], index=columns, name="A2")
    points_marked = pd.DataFrame([p1, p2])
    points_possible = pd.Series([50, 100, 20], index=columns)
    lateness = pd.DataFrame([
            pd.to_timedelta([0, 0, 50], 's'),
            pd.to_timedelta([6000, 0, 0], 's')
        ], columns=columns, index=points_marked.index)
    gradebook = gradelib.MutableGradebook(points_marked, points_possible, lateness=lateness)

    HOMEWORK = gradebook.assignments.starting_with("hw")

    gradebook.opts.lateness_fudge = 60 * 5

    result = gradebook.apply(
        gradelib.steps.PenalizeLates()
    )

    assert result.deductions == {
            "A2": {"hw01": [Percentage(1)]},
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
    gradebook.dropped.loc['A1', :] = True

    result = gradebook.apply([
        gradelib.steps.PenalizeLates(forgive=2)
    ])

    assert result.deductions == {
            "A1": {
                "hw01": [Percentage(1)],
                "lab01": [Percentage(1)],
            }
    }


# DropLowest()
# -----------------------------------------------------------------------------

def test_drop_lowest_with_callable_within():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points, maximums)
    homeworks = lambda asmts: asmts.starting_with("hw")

    # if we are dropping 1 HW, the right strategy is to drop the 50 point HW
    # for A1 and to drop the 100 point homework for A2

    # when
    actual = gradebook.apply(gradelib.steps.DropLowest(1, within=homeworks))

    # then
    assert actual.dropped.iloc[0, 1]
    assert actual.dropped.iloc[1, 2]
    assert list(actual.dropped.sum(axis=1)) == [1, 1]
    assert_gradebook_is_sound(actual)

def test_drop_lowest_on_simple_example_1():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points, maximums)
    homeworks = gradebook.assignments.starting_with("hw")

    # if we are dropping 1 HW, the right strategy is to drop the 50 point HW
    # for A1 and to drop the 100 point homework for A2

    # when
    actual = gradebook.apply(gradelib.steps.DropLowest(1, within=homeworks))

    # then
    assert actual.dropped.iloc[0, 1]
    assert actual.dropped.iloc[1, 2]
    assert list(actual.dropped.sum(axis=1)) == [1, 1]
    assert_gradebook_is_sound(actual)


def test_drop_lowest_on_simple_example_2():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.MutableGradebook(points, maximums)
    homeworks = gradebook.assignments.starting_with("hw")

    # if we are dropping 1 HW, the right strategy is to drop the 50 point HW
    # for A1 and to drop the 100 point homework for A2

    # when
    actual = gradebook.apply(gradelib.steps.DropLowest(2, within=homeworks))

    # then
    assert not actual.dropped.iloc[0, 2]
    assert not actual.dropped.iloc[1, 0]
    assert list(actual.dropped.sum(axis=1)) == [2, 2]
    assert_gradebook_is_sound(actual)


def test_drop_lowest_takes_deductions_into_account():
    # given
    columns = ["hw01", "hw02"]
    p1 = pd.Series(data=[10, 5], index=columns, name="A1")
    p2 = pd.Series(data=[10, 10], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([10, 10], index=columns)
    gradebook = gradelib.MutableGradebook(points, maximums)
    gradebook.deductions = {
            "A1": {
                "hw01": [Percentage(1)]
            }
    }

    # since A1's perfect homework has a 100% deduction, it should count as zero and be
    # dropped

    # when
    actual = gradebook.apply(gradelib.steps.DropLowest(1))

    # then
    assert actual.dropped.iloc[0, 0]
    assert list(actual.dropped.sum(axis=1)) == [1, 1]
    assert_gradebook_is_sound(actual)


def test_drop_lowest_ignores_assignments_already_dropped():
    # given
    columns = ["hw01", "hw02", "hw03", "hw04"]
    p1 = pd.Series(data=[9, 0, 7, 0], index=columns, name="A1")
    p2 = pd.Series(data=[10, 10, 10, 10], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([10, 10, 10, 10], index=columns)
    gradebook = gradelib.MutableGradebook(points, maximums)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A1", "hw04"] = True

    # since A1's perfect homeworks are already dropped, we should drop a third
    # homework, too: this will be HW03

    # when
    actual = gradebook.apply(gradelib.steps.DropLowest(1))

    # then
    assert actual.dropped.loc["A1", "hw04"]
    assert actual.dropped.loc["A1", "hw02"]
    assert actual.dropped.loc["A1", "hw03"]
    assert list(actual.dropped.sum(axis=1)) == [3, 1]
    assert_gradebook_is_sound(actual)

# Redemption
# ======================================================================================


def test_redemption_on_single_assignment_pair():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.MutableGradebook(points, maximums)

    # when
    actual = gradebook.apply(gradelib.steps.Redemption({
        'mt01 with redemption': ('mt01', 'mt01 - redemption')
    }))

    # then
    assert actual.points_marked.loc["A1", "mt01 with redemption"] == 100
    assert actual.points_marked.loc["A2", "mt01 with redemption"] == 92
    assert 'mt01' in actual.assignments
    assert 'mt01 - redemption' in actual.assignments
    assert_gradebook_is_sound(actual)

def test_redemption_on_multiple_assignment_pairs():
    # given
    columns = ["mt01", "mt01 - redemption", "mt02", "mt02 - redemption"]
    p1 = pd.Series(data=[95, 100, 45, 50], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60, 40, 35], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100, 50, 50], index=columns)
    gradebook = gradelib.MutableGradebook(points, maximums)

    # when
    actual = gradebook.apply(gradelib.steps.Redemption({
        'mt01 with redemption': ('mt01', 'mt01 - redemption'),
        'mt02 with redemption': ('mt02', 'mt02 - redemption')
    }))

    # then
    assert actual.points_marked.loc["A1", "mt01 with redemption"] == 100
    assert actual.points_marked.loc["A2", "mt01 with redemption"] == 92
    assert actual.points_marked.loc["A1", "mt02 with redemption"] == 50
    assert actual.points_marked.loc["A2", "mt02 with redemption"] == 40
    assert 'mt01' in actual.assignments
    assert 'mt01 - redemption' in actual.assignments
    assert 'mt02' in actual.assignments
    assert 'mt02 - redemption' in actual.assignments
    assert_gradebook_is_sound(actual)

def test_redemption_with_remove_parts():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.MutableGradebook(points, maximums)

    # when
    actual = gradebook.apply(gradelib.steps.Redemption({
        'mt01 with redemption': ('mt01', 'mt01 - redemption')
    }, remove_parts=True))

    # then
    assert actual.points_marked.loc["A1", "mt01 with redemption"] == 100
    assert actual.points_marked.loc["A2", "mt01 with redemption"] == 92
    assert 'mt01' not in actual.assignments
    assert 'mt01 - redemption' not in actual.assignments
    assert_gradebook_is_sound(actual)

def test_redemption_with_dropped_assignment_parts_raises():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.MutableGradebook(points, maximums)
    gradebook.dropped.loc['A1', 'mt01'] = True

    # when
    with pytest.raises(ValueError):
        actual = gradebook.apply(gradelib.steps.Redemption({
            'mt01 with redemption': ('mt01', 'mt01 - redemption')
        }))

def test_redemption_takes_deductions_into_account():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[92, 60], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.MutableGradebook(points, maximums)
    gradebook.deductions = {
            "A1": {"mt01 - redemption": [Percentage(0.5)]}
    }

    # when
    actual = gradebook.apply(gradelib.steps.Redemption({
        'mt01 with redemption': ('mt01', 'mt01 - redemption')
    }))

    # then
    assert actual.points_marked.loc["A1", "mt01 with redemption"] == 95
    assert actual.points_marked.loc["A2", "mt01 with redemption"] == 92
    assert_gradebook_is_sound(actual)

def test_redemption_with_unequal_points_possible_scales_to_the_maximum_of_the_two():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 50], index=columns, name="A1")
    p2 = pd.Series(data=[92, 40], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 50], index=columns)
    gradebook = gradelib.MutableGradebook(points, maximums)

    # when
    actual = gradebook.apply(gradelib.steps.Redemption({
        'mt01 with redemption': ('mt01', 'mt01 - redemption')
    }))

    # then
    assert actual.points_marked.loc["A1", "mt01 with redemption"] == 100
    assert actual.points_marked.loc["A2", "mt01 with redemption"] == 92
    assert actual.points_possible['mt01 with redemption'] == 100
    assert_gradebook_is_sound(actual)

def test_redemption_with_deduction():
    # given
    columns = ["mt01", "mt01 - redemption"]
    p1 = pd.Series(data=[95, 100], index=columns, name="A1")
    p2 = pd.Series(data=[50, 100], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([100, 100], index=columns)
    gradebook = gradelib.MutableGradebook(points, maximums)

    # when
    actual = gradebook.apply(gradelib.steps.Redemption({
        'mt01 with redemption': ('mt01', 'mt01 - redemption')
    }, deduction=Percentage(.25)))

    # then
    assert actual.points_marked.loc["A1", "mt01 with redemption"] == 95
    assert actual.points_marked.loc["A2", "mt01 with redemption"] == 75
    assert 'mt01' in actual.assignments
    assert 'mt01 - redemption' in actual.assignments
    assert_gradebook_is_sound(actual)