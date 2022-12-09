import pathlib

import gradelib.io.canvas

EXAMPLES_DIRECTORY = pathlib.Path(__file__).parent.parent / "examples"


def test_read_canvas_produces_assignments_in_order():
    # when
    gb = gradelib.io.canvas.read(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert gb.points_earned.columns[0] == "lab 01"
    assert gb.points_earned.columns[1] == "midterm exam"


def test_read_canvas_same_shapes_and_columns_in_all_tables():
    # when
    gb = gradelib.io.canvas.read(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert (gb.points_earned.columns == gb.points_possible.index).all()


def test_read_canvas_standardizes_pids_by_default():
    # when
    gb = gradelib.io.canvas.read(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    # the last PID is lowercased in the file, should be made uppercase
    assert set(gb.points_earned.index) == set(
        ["A12345678", "A10000000", "A16000000", "A22222222"]
    )


def test_read_canvas_standardizes_assignments_by_default():
    # when
    gb = gradelib.io.canvas.read(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert "lab 01" in gb.points_earned.columns
    assert "midterm exam" in gb.points_earned.columns


def test_read_canvas_creates_index_of_student_objects_with_names():
    # when
    gb = gradelib.io.canvas.read(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert gb.points_earned.index[0].pid == "A16000000"
    assert (
        gb.points_earned.index[0].name == "Zelda Fitzgerald"
    )  # I got the order wrong in the example CSV

    assert gb.late.index[0].pid == "A16000000"
    assert gb.late.index[0].name == "Zelda Fitzgerald"
