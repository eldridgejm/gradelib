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


def test_read_gradescope_creates_index_of_student_objects():
    # when
    points, maximums, late = gradelib.read_gradescope(EXAMPLES_DIRECTORY / "gradescope.csv")

    # then
    for ser in [points, late]:
        assert isinstance(ser.index[0], gradelib.Student)
        assert ser.index[0] == ('Zelda Fitzgerald', 'A16000000')


def test_read_gradescope_standardizes_pids_by_default():
    # when
    points, *_ = gradelib.read_gradescope(EXAMPLES_DIRECTORY / "gradescope.csv")

    # then
    # the last PID is lowercased in the file, should be made uppercase
    assert set(points.index) == set(
        [
            gradelib.Student("Justin Eldridge", "A12345678"), 
            gradelib.Student("Barack Obama", "A10000000"), 
            gradelib.Student("Zelda Fitzgerald", "A16000000"), 
            gradelib.Student("Another Eldridge", "A87654321")
        ]
    )


def test_read_gradescope_standardizes_assignments_by_default():
    # when
    points, *_ = gradelib.read_gradescope(EXAMPLES_DIRECTORY / "gradescope.csv")

    # then
    assert "homework 01" in points.columns
    assert "homework 02" in points.columns


def test_read_gradescope_without_canvas_link_produces_correct_assignments():
    # when
    path = EXAMPLES_DIRECTORY / "gradescope_not_linked_with_canvas.csv"
    points, *_ = gradelib.read_gradescope(path)

    # then
    assert points.columns[0] == "demo midterm"
    assert points.columns[1] == "fake assignment"
    assert len(points.columns) == 2


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
    assert set(points.index) == set([
        gradelib.Student("Justin Eldridge", "A12345678"), 
        gradelib.Student("Barack Obama", "A10000000"), 
        gradelib.Student("Zelda Fitzgerald", "A16000000"), 
        gradelib.Student("Someone Else", "A22222222")
        ])


def test_read_canvas_standardizes_assignments_by_default():
    # when
    points, *_ = gradelib.read_canvas(EXAMPLES_DIRECTORY / "canvas.csv")

    # then
    assert "lab 01" in points.columns
    assert "midterm exam" in points.columns
