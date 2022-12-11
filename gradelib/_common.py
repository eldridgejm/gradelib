from __future__ import annotations


def resolve_assignment_selector(within, assignments):
    if within is None:
        within = assignments

    if callable(within):
        within = within(assignments)

    if not within:
        raise ValueError("Cannot use an empty list of assignments.")

    return list(within)


def resolve_assignment_grouper(grouper, assignments: Collection[str]):
    """Resolves an assignment grouper into a dictionary.

    The resulting dictionary maps group names to lists of assignments.

    A grouper can be any of the following:

        - A dictionary mapping strings to lists of assignment names.

        - A list of strings. These strings will be interpreted as prefixes, and
          will becomes keys in the resulting dictionary. Every assignment that
          starts with a given prefix will be an element of the list that the
          key points to.

        - A Callable[[str], str] which should produce a group key when called
          on an assignment name.

    """
    if not callable(grouper):
        if not isinstance(grouper, dict):
            # should be a list of assignment prefixes
            dct = {}
            for prefix in grouper:
                dct[prefix] = [a for a in assignments if a.startswith(prefix)]
        else:
            # just a normal dictionary
            dct = grouper
    else:
        # callable, should return the group name when called on an assignment
        to_key = grouper
        dct = {}
        for assignment in assignments:
            key = to_key(assignment)
            if key not in dct:
                dct[key] = []
            dct[key].append(assignment)

    return dct
