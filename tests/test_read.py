import pathlib

import gradelib


EXAMPLES_DIRECTORY = pathlib.Path(__file__).parent / "examples"

# read_egrades_roster
# =============================================================================


def test_read_egrades_roster():
    # when
    roster = gradelib.read_egrades_roster(EXAMPLES_DIRECTORY / "egrades.csv")

    # then
    list(roster.index) == ["A12345678", "A10000000", "A16000000"]


# read_gradescope_gradebook
# =============================================================================


def test_read_gradescope_produces_assignments_in_order():
    # when
    gradebook = gradelib.read_gradescope_gradebook(
        EXAMPLES_DIRECTORY / "gradescope.csv"
    )

    # then
    assert gradebook.assignments[0] == "lab 01"
    assert gradebook.assignments[1] == "homework 01"


def test_read_gradescope_same_shapes_and_columns_in_all_tables():
    # when
    gradebook = gradelib.read_gradescope_gradebook(
        EXAMPLES_DIRECTORY / "gradescope.csv"
    )

    # then
    assert (gradebook.points.columns == gradebook.late.columns).all()
    assert gradebook.points.shape == gradebook.late.shape
    assert (gradebook.points.columns == gradebook.maximums.index).all()


def test_read_gradescope_normalizes_pids_by_default():
    # when
    gradebook = gradelib.read_gradescope_gradebook(
        EXAMPLES_DIRECTORY / "gradescope.csv"
    )

    # then
    # the last PID is lowercased in the file, should be made uppercase
    assert set(gradebook.points.index) == set(
        ["A12345678", "A10000000", "A16000000", "A87654321"]
    )


def test_read_gradescope_normalizes_assignments_by_default():
    # when
    gradebook = gradelib.read_gradescope_gradebook(
        EXAMPLES_DIRECTORY / "gradescope.csv"
    )

    # then
    assert "homework 01" in gradebook.assignments
    assert "homework 02" in gradebook.assignments


# read_canvas_gradebook
# =============================================================================


def test_read_canvas_produces_assignments_in_order():
    # when
    gradebook = gradelib.read_canvas_gradebook(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert gradebook.assignments[0] == "lab 01"
    assert gradebook.assignments[1] == "midterm exam"


def test_read_canvas_same_shapes_and_columns_in_all_tables():
    # when
    gradebook = gradelib.read_canvas_gradebook(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert (gradebook.points.columns == gradebook.maximums.index).all()


def test_read_canvas_normalizes_pids_by_default():
    # when
    gradebook = gradelib.read_canvas_gradebook(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    # the last PID is lowercased in the file, should be made uppercase
    assert set(gradebook.points.index) == set(
        ["A12345678", "A10000000", "A16000000", "A22222222"]
    )


def test_read_canvas_normalizes_assignments_by_default():
    # when
    gradebook = gradelib.read_canvas_gradebook(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert "lab 01" in gradebook.assignments
    assert "midterm exam" in gradebook.assignments
