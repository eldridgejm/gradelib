import pandas as pd

import gradelib
from gradelib.policies.exceptions import make_exceptions, ForgiveLate, Drop, Replace

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
    make_exceptions(gradebook, "Justin", [ForgiveLate("hw01")])

    # then
    assert gradebook.lateness.loc["A1", "hw01"] == pd.Timedelta(0, "s")
    assert_gradebook_is_sound(gradebook)


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
    make_exceptions(gradebook, "Justin", [ForgiveLate("hw01")])

    # then
    assert gradebook.notes == {
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
    make_exceptions(gradebook, "Justin", [Drop("hw01")])

    # then
    assert gradebook.dropped.loc["A1", "hw01"] == True
    assert_gradebook_is_sound(gradebook)


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
    make_exceptions(gradebook, "Justin", [Drop("hw01")])

    # then
    assert gradebook.dropped.loc["A1", "hw01"] == True
    assert gradebook.notes == {"A1": {"drops": ["Exception applied: Hw01 dropped."]}}


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
    make_exceptions(gradebook, "Justin", [Replace("hw02", with_="hw01")])

    # then
    assert gradebook.points_earned.loc["A1", "hw01"] == 9
    assert gradebook.points_earned.loc["A1", "hw02"] == 9
    assert_gradebook_is_sound(gradebook)


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
    make_exceptions(gradebook, "Justin", [Replace("hw01", with_="hw02")])

    # then
    assert gradebook.points_earned.loc["A1", "hw01"] == 7.5
    assert gradebook.points_earned.loc["A1", "hw02"] == 15
    assert_gradebook_is_sound(gradebook)


def test_make_exceptions_with_replace_using_points():
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
    make_exceptions(
        gradebook,
        "Justin",
        [Replace("hw02", with_=gradelib.Points(12))],
    )

    # then
    assert gradebook.points_earned.loc["A1", "hw01"] == 9
    assert gradebook.points_earned.loc["A1", "hw02"] == 12
    assert_gradebook_is_sound(gradebook)


def test_make_exceptions_with_replace_using_percentage_of_points_possible():
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
    make_exceptions(
        gradebook,
        "Justin",
        [Replace("hw02", with_=gradelib.Percentage(0.5))],
    )

    # then
    assert gradebook.points_earned.loc["A1", "hw01"] == 9
    assert gradebook.points_earned.loc["A1", "hw02"] == 5
    assert_gradebook_is_sound(gradebook)
