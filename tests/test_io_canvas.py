import pathlib

import gradelib.io.canvas

EXAMPLES_DIRECTORY = pathlib.Path(__file__).parent / "examples"


def test_read_canvas_produces_assignments_in_order():
    # when
    points, *_ = gradelib.io.canvas.read(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert points.columns[0] == "lab 01"
    assert points.columns[1] == "midterm exam"


def test_read_canvas_same_shapes_and_columns_in_all_tables():
    # when
    points, maximums = gradelib.io.canvas.read(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert (points.columns == maximums.index).all()


def test_read_canvas_standardizes_pids_by_default():
    # when
    points, *_ = gradelib.io.canvas.read(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    # the last PID is lowercased in the file, should be made uppercase
    assert set(points.index) == set(
        ["A12345678", "A10000000", "A16000000", "A22222222"]
    )


def test_read_canvas_standardizes_assignments_by_default():
    # when
    points, *_ = gradelib.io.canvas.read(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert "lab 01" in points.columns
    assert "midterm exam" in points.columns
