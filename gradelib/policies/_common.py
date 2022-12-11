def resolve_within(gradebook, within):
    if within is None:
        within = gradebook.assignments

    if callable(within):
        within = within(gradebook.assignments)

    if not within:
        raise ValueError("Cannot use an empty list of assignments.")

    return list(within)
