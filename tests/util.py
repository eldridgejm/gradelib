def assert_gradebook_is_sound(gradebook):
    assert (
        gradebook.points_earned.shape
        == gradebook.dropped.shape
        == gradebook.lateness.shape
    )
    assert (gradebook.points_earned.columns == gradebook.dropped.columns).all()
    assert (gradebook.points_earned.columns == gradebook.lateness.columns).all()
    assert (gradebook.points_earned.index == gradebook.dropped.index).all()
    assert (gradebook.points_earned.index == gradebook.lateness.index).all()
    assert (gradebook.points_earned.columns == gradebook.points_possible.index).all()
