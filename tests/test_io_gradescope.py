import pathlib

import pandas as pd

import gradelib.io.gradescope

EXAMPLES_DIRECTORY = pathlib.Path(__file__).parent / "examples"

# read_gradescope
# =============================================================================


def test_read_gradescope_produces_assignments_in_order():
    # when
    gb = gradelib.io.gradescope.read(EXAMPLES_DIRECTORY / "gradescope.csv")

    # then
    assert gb.points.columns[0] == "lab 01"
    assert gb.points.columns[1] == "homework 01"


def test_read_gradescope_same_shapes_and_columns_in_all_tables():
    # when
    gb = gradelib.io.gradescope.read(
        EXAMPLES_DIRECTORY / "gradescope.csv"
    )

    # then
    assert (gb.points.columns == gb.late.columns).all()
    assert gb.points.shape == gb.late.shape
    assert (gb.points.columns == gb.maximums.index).all()


def test_read_gradescope_standardizes_pids_by_default():
    # when
    gb = gradelib.io.gradescope.read(EXAMPLES_DIRECTORY / "gradescope.csv")

    # then
    # the last PID is lowercased in the file, should be made uppercase
    assert set(gb.points.index) == set(
        ["A12345678", "A10000000", "A16000000", "A87654321"]
    )


def test_read_gradescope_standardizes_assignments_by_default():
    # when
    gb = gradelib.io.gradescope.read(EXAMPLES_DIRECTORY / "gradescope.csv")

    # then
    assert "homework 01" in gb.points.columns
    assert "homework 02" in gb.points.columns

def test_read_gradescope_creates_index_of_student_objects_with_names():
    # when
    gb = gradelib.io.gradescope.read(EXAMPLES_DIRECTORY / "gradescope.csv")

    # then
    assert gb.points.index[0].pid == "A16000000"
    assert gb.points.index[0].name == "Fitzgerald Zelda" # I got the order wrong in the example CSV

    assert gb.late.index[0].pid == "A16000000"
    assert gb.late.index[0].name == "Fitzgerald Zelda" # I got the order wrong in the example CSV

def test_read_gradescope_without_canvas_link_produces_correct_assignments():
    # when
    path = EXAMPLES_DIRECTORY / "gradescope_not_linked_with_canvas.csv"
    gb = gradelib.io.gradescope.read(path)

    # then
    assert gb.points.columns[0] == "demo midterm"
    assert gb.points.columns[1] == "fake assignment"
    assert len(gb.points.columns) == 2


def test_read_gradescope_keeps_lateness_as_timedelta():
    gb = gradelib.io.gradescope.read(
        EXAMPLES_DIRECTORY / "gradescope-with-5m-late.csv"
    )
    # 22 hours, 37 minutes, 22 seconds
    assert gb.lateness.iloc[0]['lab 07'] == pd.Timedelta(hours=22, minutes=37, seconds=22)
