import pathlib

import pytest
import pandas as pd
import numpy as np

import gradelib


EXAMPLES_DIRECTORY = pathlib.Path(__file__).parent / "examples"
GRADESCOPE_EXAMPLE = gradelib.Gradebook.from_gradescope(
    EXAMPLES_DIRECTORY / "gradescope.csv"
)
CANVAS_EXAMPLE = gradelib.Gradebook.from_canvas(EXAMPLES_DIRECTORY / "canvas.csv")

# the canvas example has Lab 01, which is also in Gradescope. Let's remove it
CANVAS_WITHOUT_LAB_EXAMPLE = gradelib.Gradebook(
    points=CANVAS_EXAMPLE.points.drop(columns="lab 01"),
    maximums=CANVAS_EXAMPLE.maximums.drop(index="lab 01"),
    late=CANVAS_EXAMPLE.late.drop(columns="lab 01"),
    dropped=CANVAS_EXAMPLE.dropped.drop(columns="lab 01"),
)

# given
ROSTER = gradelib.read_egrades_roster(EXAMPLES_DIRECTORY / "egrades.csv")


def assert_gradebook_is_sound(gradebook):
    assert gradebook.points.shape == gradebook.dropped.shape == gradebook.late.shape
    assert (gradebook.points.columns == gradebook.dropped.columns).all()
    assert (gradebook.points.columns == gradebook.late.columns).all()
    assert (gradebook.points.index == gradebook.dropped.index).all()
    assert (gradebook.points.index == gradebook.late.index).all()
    assert (gradebook.points.columns == gradebook.maximums.index).all()


# assignments property
# -----------------------------------------------------------------------------


def test_assignments_are_produced_in_order():
    assert list(GRADESCOPE_EXAMPLE.assignments) == list(
        GRADESCOPE_EXAMPLE.points.columns
    )


# restrict_pids()
# -----------------------------------------------------------------------------


def test_restrict_pids():
    # when
    actual = GRADESCOPE_EXAMPLE.restrict_pids(ROSTER.index)

    # then
    assert len(actual.pids) == 3
    assert_gradebook_is_sound(actual)


def test_restrict_pids_raises_if_pid_does_not_exist():
    # given
    pids = ["A12345678", "ADNEDNE00"]

    # when
    with pytest.raises(KeyError):
        actual = GRADESCOPE_EXAMPLE.restrict_pids(pids)


# restrict_assignments()
# -----------------------------------------------------------------------------


def test_restrict_assignments():
    # when
    actual = GRADESCOPE_EXAMPLE.restrict_assignments(["homework 01", "homework 02"])

    # then
    assert set(actual.assignments) == {"homework 01", "homework 02"}
    assert_gradebook_is_sound(actual)


def test_restrict_assignments_raises_if_assignment_does_not_exist():
    # given
    assignments = ["homework 01", "this aint an assignment"]

    # then
    with pytest.raises(KeyError):
        GRADESCOPE_EXAMPLE.restrict_assignments(assignments)


# combine()
# -----------------------------------------------------------------------------


def test_combine_with_restrict_pids():
    # when
    combined = gradelib.Gradebook.combine(
        [GRADESCOPE_EXAMPLE, CANVAS_WITHOUT_LAB_EXAMPLE], restrict_pids=ROSTER.index
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


# forgive_lates()
# -----------------------------------------------------------------------------


def test_forgive_lates():
    # when
    labs = GRADESCOPE_EXAMPLE.assignments.starting_with("lab")
    actual = GRADESCOPE_EXAMPLE.forgive_lates(n=3, within=labs)

    # then
    assert list(actual.number_of_lates(within=labs)) == [0, 1, 0, 0]
    assert_gradebook_is_sound(actual)


def test_forgive_lates_with_empty_assignment_list_raises():
    # when
    with pytest.raises(ValueError):
        actual = GRADESCOPE_EXAMPLE.forgive_lates(n=3, within=[])


def test_forgive_lates_forgives_the_first_n_lates():
    # by "first", we mean in the order specified by the `within` argument
    # student A10000000 had late lab 01, 02, 03, and 07

    assignments = ["lab 02", "lab 07", "lab 01", "lab 03"]

    # when
    actual = GRADESCOPE_EXAMPLE.forgive_lates(n=2, within=assignments)

    # then
    assert not actual.late.loc["A10000000", "lab 02"]
    assert not actual.late.loc["A10000000", "lab 07"]
    assert actual.late.loc["A10000000", "lab 01"]
    assert actual.late.loc["A10000000", "lab 03"]


def test_forgive_lates_does_not_forgive_dropped():
    # given
    labs = GRADESCOPE_EXAMPLE.assignments.starting_with("lab")
    dropped = GRADESCOPE_EXAMPLE.dropped.copy()
    dropped.iloc[:, :] = True
    example = gradelib.Gradebook(
        points=GRADESCOPE_EXAMPLE.points,
        maximums=GRADESCOPE_EXAMPLE.maximums,
        late=GRADESCOPE_EXAMPLE.late,
        dropped=dropped,
    )

    # when
    actual = example.forgive_lates(n=3, within=labs)

    # then
    assert list(actual.number_of_lates(within=labs)) == [1, 4, 2, 2]
    assert_gradebook_is_sound(actual)


# drop_lowest()
# -----------------------------------------------------------------------------


def test_drop_lowest_on_simple_example_1():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    homeworks = gradebook.assignments.starting_with("hw")

    # if we are dropping 1 HW, the right strategy is to drop the 50 point HW
    # for A1 and to drop the 100 point homework for A2

    # when
    actual = gradebook.drop_lowest(1, within=homeworks)

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
    gradebook = gradelib.Gradebook(points, maximums)
    homeworks = gradebook.assignments.starting_with("hw")

    # if we are dropping 1 HW, the right strategy is to drop the 50 point HW
    # for A1 and to drop the 100 point homework for A2

    # when
    actual = gradebook.drop_lowest(2, within=homeworks)

    # then
    assert not actual.dropped.iloc[0, 2]
    assert not actual.dropped.iloc[1, 0]
    assert list(actual.dropped.sum(axis=1)) == [2, 2]
    assert_gradebook_is_sound(actual)


def test_drop_lowest_counts_lates_as_zeros():
    # given
    columns = ["hw01", "hw02"]
    p1 = pd.Series(data=[10, 5], index=columns, name="A1")
    p2 = pd.Series(data=[10, 10], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([10, 10], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    gradebook.late.iloc[0, 0] = True

    # since A1's perfect homework is late, it should count as zero and be
    # dropped

    # when
    actual = gradebook.drop_lowest(1)

    # then
    assert actual.dropped.iloc[0, 0]
    assert list(actual.dropped.sum(axis=1)) == [1, 1]
    assert_gradebook_is_sound(actual)


def test_drop_lowest_ignores_assignments_alread_dropped():
    # given
    columns = ["hw01", "hw02", "hw03", "hw04"]
    p1 = pd.Series(data=[9, 0, 7, 0], index=columns, name="A1")
    p2 = pd.Series(data=[10, 10, 10, 10], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([10, 10, 10, 10], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    gradebook.dropped.loc["A1", "hw02"] = True
    gradebook.dropped.loc["A1", "hw04"] = True

    # since A1's perfect homeworks are already dropped, we should drop a third
    # homework, too: this will be HW03

    # when
    actual = gradebook.drop_lowest(1)

    # then
    assert actual.dropped.loc["A1", "hw04"]
    assert actual.dropped.loc["A1", "hw02"]
    assert actual.dropped.loc["A1", "hw03"]
    assert list(actual.dropped.sum(axis=1)) == [3, 1]
    assert_gradebook_is_sound(actual)


# give_equal_weights()
# -----------------------------------------------------------------------------


def test_give_equal_weights_on_example():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    homeworks = gradebook.assignments.starting_with("hw")

    # when
    actual = gradebook.give_equal_weights(within=homeworks)

    # then
    assert actual.maximums.loc["hw01"] == 1
    assert actual.maximums.loc["hw02"] == 1
    assert actual.maximums.loc["hw03"] == 1
    assert actual.maximums.loc["lab01"] == 20
    assert actual.points.loc["A1", "hw01"] == 1 / 2
    assert actual.points.loc["A1", "hw02"] == 30 / 50


# score()
# -----------------------------------------------------------------------------


def test_score_on_simple_example():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    homeworks = gradebook.assignments.starting_with("hw")

    # when
    actual = gradebook.score(homeworks)

    # then
    assert np.allclose(actual.values, [121 / 152, 24 / 152], atol=1e-6)


def test_score_counts_lates_as_zero():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    gradebook.late.loc["A1", "hw01"] = True
    gradebook.late.loc["A1", "hw03"] = True
    gradebook.late.loc["A2", "hw03"] = True
    homeworks = gradebook.assignments.starting_with("hw")

    # when
    actual = gradebook.score(homeworks)

    # then
    assert np.allclose(actual.values, [30 / 152, 9 / 152], atol=1e-6)


def test_score_ignores_dropped_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
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
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    homeworks = gradebook.assignments.starting_with("hw")

    # when
    earned, available = gradebook.total(homeworks)

    # then
    assert np.allclose(earned.values, [121, 24], atol=1e-6)
    assert np.allclose(available.values, [152, 152], atol=1e-6)


def test_total_counts_lates_as_zero():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    gradebook.late.loc["A1", "hw01"] = True
    gradebook.late.loc["A1", "hw03"] = True
    gradebook.late.loc["A2", "hw03"] = True
    homeworks = gradebook.assignments.starting_with("hw")

    # when
    earned, available = gradebook.total(homeworks)

    # then
    assert np.allclose(earned.values, [30, 9], atol=1e-6)
    assert np.allclose(available.values, [152, 152], atol=1e-6)


def test_total_ignores_dropped_assignments():
    # given
    columns = ["hw01", "hw02", "hw03", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    gradebook.dropped.loc["A1", "hw01"] = True
    gradebook.dropped.loc["A1", "hw03"] = True
    gradebook.dropped.loc["A2", "hw03"] = True
    homeworks = gradebook.assignments.starting_with("hw")

    # when
    earned, available = gradebook.total(homeworks)

    # then
    assert np.allclose(earned.values, [30, 9], atol=1e-6)
    assert np.allclose(available.values, [50, 52], atol=1e-6)


# unify()
# -----------------------------------------------------------------------------


def test_unify():
    """test that points / maximums are added across unified assignments"""
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    # when
    result = gradebook.unify(HOMEWORK_01_PARTS, "hw01")

    # then
    assert len(result.assignments) == 3
    assert result.maximums["hw01"] == 52
    assert result.points.loc["A1", "hw01"] == 31

    assert result.maximums.shape[0] == 3
    assert result.late.shape[1] == 3
    assert result.dropped.shape[1] == 3
    assert result.points.shape[1] == 3


def test_unify_considers_new_assignment_late_if_any_part_late():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    gradebook.late.loc["A1", "hw01"] = True
    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    # when
    result = gradebook.unify(HOMEWORK_01_PARTS, "hw01")

    # then
    assert result.late.loc["A1", "hw01"] == True


def test_unify_raises_if_any_part_is_dropped():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    gradebook.dropped.loc["A1", "hw01"] = True
    HOMEWORK_01_PARTS = gradebook.assignments.starting_with("hw01")

    with pytest.raises(ValueError):
        result = gradebook.unify(HOMEWORK_01_PARTS, "hw01")


# add_assignment()
# -----------------------------------------------------------------------------


def test_add_assignment():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    assignment_points = pd.Series([10, 20], index=["A1", "A2"])
    assignment_max = 20
    assignment_late = pd.Series([True, False], index=["A1", "A2"])
    assignment_dropped = pd.Series([False, True], index=["A1", "A2"])

    # when
    result = gradebook.add_assignment(
        "new", assignment_points, 20, late=assignment_late, dropped=assignment_dropped
    )

    # then
    assert len(result.assignments) == 5
    assert result.points.loc["A1", "new"] == 10
    assert result.maximums.loc["new"] == 20


def test_add_assignment_default_none_dropped_or_late():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    assignment_points = pd.Series([10, 20], index=["A1", "A2"])
    assignment_max = 20

    # when
    result = gradebook.add_assignment("new", assignment_points, 20,)

    # then
    assert result.late.loc["A1", "new"] == False
    assert result.dropped.loc["A1", "new"] == False


def test_add_assignment_raises_on_missing_student():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # A2 is missing
    assignment_points = pd.Series([10], index=["A1"])
    assignment_max = 20

    # when
    with pytest.raises(ValueError):
        gradebook.add_assignment(
            "new", assignment_points, 20,
        )


def test_add_assignment_raises_on_unknown_student():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # foo is unknown
    assignment_points = pd.Series([10, 20, 30], index=["A1", "A2", "A3"])
    assignment_max = 20

    # when
    with pytest.raises(ValueError):
        gradebook.add_assignment(
            "new", assignment_points, 20,
        )


def test_add_assignment_raises_if_duplicate_name():
    # given
    columns = ["hw01", "hw01 - programming", "hw02", "lab01"]
    p1 = pd.Series(data=[1, 30, 90, 20], index=columns, name="A1")
    p2 = pd.Series(data=[2, 7, 15, 20], index=columns, name="A2")
    points = pd.DataFrame([p1, p2])
    maximums = pd.Series([2, 50, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    assignment_points = pd.Series([10, 20], index=["A1", "A2"])
    assignment_max = 20

    # when
    with pytest.raises(ValueError):
        gradebook.add_assignment(
            "hw01", assignment_points, 20,
        )
