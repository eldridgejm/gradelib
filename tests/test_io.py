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


# read_gradescope
# =============================================================================


def test_read_gradescope_produces_assignments_in_order():
    # when
    points, *_ = gradelib.read_gradescope(EXAMPLES_DIRECTORY / "gradescope.csv")

    # then
    assert points.columns[0] == "lab 01"
    assert points.columns[1] == "homework 01"


def test_read_gradescope_same_shapes_and_columns_in_all_tables():
    # when
    points, maximums, late = gradelib.read_gradescope(
        EXAMPLES_DIRECTORY / "gradescope.csv"
    )

    # then
    assert (points.columns == late.columns).all()
    assert points.shape == late.shape
    assert (points.columns == maximums.index).all()


def test_read_gradescope_standardizes_pids_by_default():
    # when
    points, *_ = gradelib.read_gradescope(EXAMPLES_DIRECTORY / "gradescope.csv")

    # then
    # the last PID is lowercased in the file, should be made uppercase
    assert set(points.index) == set(
        ["A12345678", "A10000000", "A16000000", "A87654321"]
    )


def test_read_gradescope_standardizes_assignments_by_default():
    # when
    points, *_ = gradelib.read_gradescope(EXAMPLES_DIRECTORY / "gradescope.csv")

    # then
    assert "homework 01" in points.columns
    assert "homework 02" in points.columns


# read_canvas
# =============================================================================


def test_read_canvas_produces_assignments_in_order():
    # when
    points, *_ = gradelib.read_canvas(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert points.columns[0] == "lab 01"
    assert points.columns[1] == "midterm exam"


def test_read_canvas_same_shapes_and_columns_in_all_tables():
    # when
    points, maximums = gradelib.read_canvas(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert (points.columns == maximums.index).all()


def test_read_canvas_standardizes_pids_by_default():
    # when
    points, *_ = gradelib.read_canvas(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    # the last PID is lowercased in the file, should be made uppercase
    assert set(points.index) == set(
        ["A12345678", "A10000000", "A16000000", "A22222222"]
    )


def test_read_canvas_standardizes_assignments_by_default():
    # when
    points, *_ = gradelib.read_canvas(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert "lab 01" in points.columns
    assert "midterm exam" in points.columns
