
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


