import typing

import pandas as pd


def _empty_mask_like(table):
    """Given a dataframe, create another just like it with every entry False."""
    empty = table.copy()
    empty.iloc[:, :] = False
    return empty.astype(bool)


def _resolve_assignment_grouper(grouper, assignments: typing.Collection[str]):
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
                dct[prefix] = {a for a in assignments if a.startswith(prefix)}
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


def _combine_assignment_parts(gb, new_name, parts):
    """A helper function to combine assignments under the new name."""
    parts = list(parts)
    if gb.dropped[parts].any(axis=None):
        raise ValueError("Cannot combine assignments with drops.")

    assignment_points = gb.points_earned[parts].sum(axis=1)
    assignment_max = gb.points_possible[parts].sum()
    assignment_lateness = gb.lateness[parts].max(axis=1)

    gb.points_earned[new_name] = assignment_points
    gb.points_possible[new_name] = assignment_max
    gb.lateness[new_name] = assignment_lateness

    # we're assuming that dropped was not set; we need to provide an empy
    # mask here, else ._replace will use the existing larger dropped table
    # of gb, which contains all parts
    gb.dropped = _empty_mask_like(gb.points_earned)

    gb.remove_assignments(set(parts) - {new_name})


def combine_assignment_parts(gb, selector):
    """Combine the assignment parts into one assignment with the new name.

    Sometimes assignments may have several parts which are recorded
    separately in the grading software. For instance, a homework might have
    a written part and a programming part. This method makes it easy to
    combine these parts into a single assignment.

    The individual assignment parts are removed from the gradebook.

    The new marked points and possible points are calculated by addition.
    The lateness of the new assignment is the *maximum* lateness of any of
    its parts.

    Points are propagated unchanged, but Percentage objects are converted
    to Points according to the ratio of the part's value to the total
    points possible. For example, if the first part is worth 70 points, and
    the second part is worth 30 points, and a 25% Percentage is applied to
    the second part, it is converted to a 25% * 30 = 7.5 point Points.

    It is unclear what the result should be if any of the assignments to be
    unified has been dropped, but other parts have not. For this reason,
    this method will raise a `ValueError` if *any* of the parts have been
    dropped.

    Assignment groups are automatically reset to prevent errors. It is
    suggested that the gradebook's assignments be finalized before setting
    the assignment groups.

    Parameters
    ----------
    selector : Mapping[str, Collection[str]]
        Either: 1) a mapping whose keys are new assignment names, and whose
        values are collections of assignments that should be unified under
        their common key; 2) a list of prefixes; each prefix defines a
        group that should be combined; or 3) a callable which maps
        assignment names to new assignment by which they should be grouped.

    Raises
    ------
    ValueError
        If any of the assignments to be unified is marked as dropped. See above for
        rationale.

    Example
    -------

    Assuming the gradebook has assignments named `homework 01`, `homework 01 - programming`,
    `homework 02`, `homework 02 - programming`, etc., the following will "combine" the
    assignments into `homework 01`, `homework 02`, etc:

        >>> gradebook.combine_assignment_parts(lambda s: s.split('-')[0].strip())

    Alternatively, you could write:

        >>> gradebook.combine_assignment_parts(["homework 01", "homework 02"])

    Or:

        >>> gradebook.combine_assignment_parts({
            'homework 01': {'homework 01', 'homework 01 - programming'},
            'homework 02': {'homework 02', 'homework 02 - programming'}
            })


    """
    dct = _resolve_assignment_grouper(selector, gb.assignments)

    for key, value in dct.items():
        _combine_assignment_parts(gb, key, value)

    gb.assignment_groups = {}

def _combine_assignment_versions(gb, new_name, versions):
    """A helper function to combine assignments under the new name."""
    versions = list(versions)
    if gb.dropped[versions].any(axis=None):
        raise ValueError("Cannot combine assignments with drops.")

    # check that points are not earned in multiple versions
    assignments_turned_in = (~pd.isna(gb.points_earned)).sum(axis=1)
    if (assignments_turned_in > 1).any():
        students = assignments_turned_in[assignments_turned_in > 1].index
        msg = f"{list(students)} turned in more than one version."
        raise ValueError(msg)

    # check that there's no lateness in any version
    total_lateness = gb.lateness[versions].sum(axis=1)
    if total_lateness.any():
        msg = "Cannot combine versions when some have been turned in late."
        raise ValueError(msg)

    assignment_points = gb.points_earned[versions].max(axis=1)
    assignment_max = gb.points_possible[versions[0]]
    assignment_lateness = gb.lateness[versions].max(axis=1)

    gb.points_earned[new_name] = assignment_points
    gb.points_possible[new_name] = assignment_max
    gb.lateness[new_name] = assignment_lateness

    # we're assuming that dropped was not set; we need to provide an empy
    # mask here, else ._replace will use the existing larger dropped table
    # of gb, which contains all versions
    gb.dropped = _empty_mask_like(gb.points_earned)

    gb.remove_assignments(set(versions) - {new_name})

def combine_assignment_versions(gb, selector):
    """Combine the assignment versions into one single assignment with the new name.

    Sometimes assignments may have several versions which are recorded separately
    in the grading software. For instance, multiple versions of a midterm may be
    distributed to prevent cheating.

    The individual assignment versions are removed from the gradebook and
    are unified into a single new version.

    It is assumed that all assignment versions have the same number of
    points possible. If this is not the case, a `ValueError` is raised.

    Similarly, it is assumed that no student earns points for more than one
    of the versions. If this is not true, a `ValueError` is raised.

    It is unclear what the result should be if any of the assignments to be
    unified has been dropped or is late, but other parts have not. If
    either of these assumptions are violated, this method will raise a
    `ValueError`.

    Groups are updated so that the versions no longer appear in any group, but
    new groups are not created.

    Parameters
    ----------
    selector : Mapping[str, Collection[str]]
        Either: 1) a mapping whose keys are new assignment names, and whose
        values are collections of assignments that should be unified under
        their common key; 2) a list of prefixes; each prefix defines a
        group that should be combined; or 3) a callable which maps
        assignment names to new assignment by which they should be grouped.

    Raises
    ------
    ValueError
        If any of the assumptions are violated. See above.

    Example
    -------

    Assuming the gradebook has assignments named `midterm - version a`,
    `midterm - version b`, `midterm - version c`, etc., the following will
    "combine" the assignments into `midterm`:

        >>> gradebook.combine_assignment_versions(lambda s: s.split('-')[0].strip())

    Alternatively, you could write:

        >>> gradebook.combine_assignment_versions(["midterm"])

    Or:

        >>> gradebook.combine_assignment_versions({
            'midterm': {'midterm - version a', 'midterm - version b', 'midterm - 'version c'},
            })


    """
    dct = _resolve_assignment_grouper(selector, gb.assignments)

    for key, value in dct.items():
        _combine_assignment_versions(gb, key, value)
