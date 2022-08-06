import pathlib

import gradelib.io.gradescope

EXAMPLES_DIRECTORY = pathlib.Path(__file__).parent / "examples"

# read_gradescope
# =============================================================================


def test_read_gradescope_produces_assignments_in_order():
    # when
    points, *_ = gradelib.io.gradescope.read(EXAMPLES_DIRECTORY / "gradescope.csv")

    # then
    assert points.columns[0] == "lab 01"
    assert points.columns[1] == "homework 01"


def test_read_gradescope_same_shapes_and_columns_in_all_tables():
    # when
    points, maximums, late = gradelib.io.gradescope.read(
        EXAMPLES_DIRECTORY / "gradescope.csv"
    )

    # then
    assert (points.columns == late.columns).all()
    assert points.shape == late.shape
    assert (points.columns == maximums.index).all()


def test_read_gradescope_standardizes_pids_by_default():
    # when
    points, *_ = gradelib.io.gradescope.read(EXAMPLES_DIRECTORY / "gradescope.csv")

    # then
    # the last PID is lowercased in the file, should be made uppercase
    assert set(points.index) == set(
        ["A12345678", "A10000000", "A16000000", "A87654321"]
    )


def test_read_gradescope_standardizes_assignments_by_default():
    # when
    points, *_ = gradelib.io.gradescope.read(EXAMPLES_DIRECTORY / "gradescope.csv")

    # then
    assert "homework 01" in points.columns
    assert "homework 02" in points.columns


def test_read_gradescope_without_canvas_link_produces_correct_assignments():
    # when
    path = EXAMPLES_DIRECTORY / "gradescope_not_linked_with_canvas.csv"
    points, *_ = gradelib.io.gradescope.read(path)

    # then
    assert points.columns[0] == "demo midterm"
    assert points.columns[1] == "fake assignment"
    assert len(points.columns) == 2
