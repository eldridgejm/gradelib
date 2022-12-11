
import pandas as pd

import gradelib

from util import assert_gradebook_is_sound

def test_make_exceptions_with_forgive_lates():
    # given
    columns = ["hw01", "hw02", "hw03", "hw04"]
    p1 = pd.Series(data=[9, 0, 7, 0], index=columns)
    p2 = pd.Series(data=[10, 10, 10, 10], index=columns)
    points = pd.DataFrame(
        [p1, p2],
        index=[gradelib.Student("A1", "Justin"), gradelib.Student("A2", "Steve")],
    )
    maximums = pd.Series([10, 10, 10, 10], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    gradebook.lateness.loc["A1", "hw01"] = pd.Timedelta(5000, "s")

    # when
    actual = gradelib.grading.MakeExceptions(
        "Justin", [gradelib.grading.ForgiveLate("hw01")]
    )(gradebook)

    # then
    assert actual.lateness.loc["A1", "hw01"] == pd.Timedelta(0, "s")
    assert_gradebook_is_sound(actual)


def test_make_exceptions_with_forgive_lates_adds_note():
    # given
    columns = ["hw01", "hw02", "hw03", "hw04"]
    p1 = pd.Series(data=[9, 0, 7, 0], index=columns)
    p2 = pd.Series(data=[10, 10, 10, 10], index=columns)
    points = pd.DataFrame(
        [p1, p2],
        index=[gradelib.Student("A1", "Justin"), gradelib.Student("A2", "Steve")],
    )
    maximums = pd.Series([10, 10, 10, 10], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)
    gradebook.lateness.loc["A1", "hw01"] = pd.Timedelta(5000, "s")

    # when
    actual = gradelib.grading.MakeExceptions(
        "Justin", [gradelib.grading.ForgiveLate("hw01")]
    )(gradebook)

    # then
    assert actual.notes == {
        "A1": {"lates": ["Exception applied: late Hw01 is forgiven."]}
    }


def test_make_exceptions_with_drop():
    # given
    columns = ["hw01", "hw02", "hw03", "hw04"]
    p1 = pd.Series(data=[9, 0, 7, 0], index=columns)
    p2 = pd.Series(data=[10, 10, 10, 10], index=columns)
    points = pd.DataFrame(
        [p1, p2],
        index=[gradelib.Student("A1", "Justin"), gradelib.Student("A2", "Steve")],
    )
    maximums = pd.Series([10, 10, 10, 10], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    actual = gradelib.grading.MakeExceptions(
        "Justin", [gradelib.grading.Drop("hw01")]
    )(gradebook)

    # then
    assert actual.dropped.loc["A1", "hw01"] == True
    assert_gradebook_is_sound(actual)


def test_make_exceptions_with_drop_adds_note():
    # given
    columns = ["hw01", "hw02", "hw03", "hw04"]
    p1 = pd.Series(data=[9, 0, 7, 0], index=columns)
    p2 = pd.Series(data=[10, 10, 10, 10], index=columns)
    points = pd.DataFrame(
        [p1, p2],
        index=[gradelib.Student("A1", "Justin"), gradelib.Student("A2", "Steve")],
    )
    maximums = pd.Series([10, 10, 10, 10], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    actual = gradelib.grading.MakeExceptions(
        "Justin", [gradelib.grading.Drop("hw01")]
    )(gradebook)

    # then
    assert actual.dropped.loc["A1", "hw01"] == True
    assert actual.notes == {"A1": {"drops": ["Exception applied: Hw01 dropped."]}}


def test_make_exceptions_with_replace():
    # given
    columns = ["hw01", "hw02", "hw03", "hw04"]
    p1 = pd.Series(data=[9, 0, 7, 0], index=columns)
    p2 = pd.Series(data=[10, 10, 10, 10], index=columns)
    points = pd.DataFrame(
        [p1, p2],
        index=[gradelib.Student("A1", "Justin"), gradelib.Student("A2", "Steve")],
    )
    maximums = pd.Series([10, 10, 10, 10], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    actual = gradelib.grading.MakeExceptions(
        "Justin", [gradelib.grading.Replace("hw02", with_="hw01")]
    )(gradebook)

    # then
    assert actual.points_earned.loc["A1", "hw01"] == 9
    assert actual.points_earned.loc["A1", "hw02"] == 9
    assert_gradebook_is_sound(actual)


def test_make_exceptions_with_replace_scales_using_points_possible():
    # given
    columns = ["hw01", "hw02", "hw03", "hw04"]
    p1 = pd.Series(data=[9, 15, 7, 0], index=columns)
    p2 = pd.Series(data=[10, 10, 10, 10], index=columns)
    points = pd.DataFrame(
        [p1, p2],
        index=[gradelib.Student("A1", "Justin"), gradelib.Student("A2", "Steve")],
    )
    maximums = pd.Series([10, 20, 10, 10], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    actual = gradelib.grading.MakeExceptions(
        "Justin", [gradelib.grading.Replace("hw01", with_="hw02")]
    )(gradebook)

    # then
    assert actual.points_earned.loc["A1", "hw01"] == 7.5
    assert actual.points_earned.loc["A1", "hw02"] == 15
    assert_gradebook_is_sound(actual)


def test_make_exceptions_with_override():
    # given
    columns = ["hw01", "hw02", "hw03", "hw04"]
    p1 = pd.Series(data=[9, 0, 7, 0], index=columns)
    p2 = pd.Series(data=[10, 10, 10, 10], index=columns)
    points = pd.DataFrame(
        [p1, p2],
        index=[gradelib.Student("A1", "Justin"), gradelib.Student("A2", "Steve")],
    )
    maximums = pd.Series([10, 10, 10, 10], index=columns)
    gradebook = gradelib.Gradebook(points, maximums)

    # when
    actual = gradelib.grading.MakeExceptions(
        "Justin",
        [
            gradelib.grading.Override("hw01", gradelib.Percentage(0.5)),
            gradelib.grading.Override("hw02", gradelib.Points(8)),
        ],
    )(gradebook)

    # then
    assert actual.points_earned.loc["A1", "hw01"] == 5
    assert actual.points_earned.loc["A1", "hw02"] == 8
    assert_gradebook_is_sound(actual)
