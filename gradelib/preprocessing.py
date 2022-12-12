"""Tools for preprocessing Gradebooks before grading."""

from __future__ import annotations

import typing

import pandas as pd

from .core import AssignmentGrouper
from ._common import resolve_assignment_grouper

# private helper functions =============================================================


def _empty_mask_like(table):
    """Given a dataframe, create another just like it with every entry False."""
    empty = table.copy()
    empty.iloc[:, :] = False
    return empty.astype(bool)


# public functions =====================================================================

# combine_assignment_parts -------------------------------------------------------------


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


def combine_assignment_parts(gb, grouper: AssignmentGrouper):
    """Combine the assignment parts into one assignment with the new name.

    Sometimes assignments may have several parts which are recorded
    separately in the grading software. For instance, a homework might have
    a written part and a programming part. This method makes it easy to
    combine these parts into a single assignment.

    The individual assignment parts are removed from the gradebook.

    The new marked points and possible points are calculated by addition.
    The lateness of the new assignment is the *maximum* lateness of any of
    its parts.

    It is unclear what the result should be if any of the assignments to be
    unified has been dropped, but other parts have not. For this reason,
    this method will raise a `ValueError` if *any* of the parts have been
    dropped.

    Assignment groups are automatically reset to prevent errors. It is
    suggested that the gradebook's assignments be finalized before setting
    the assignment groups.

    Parameters
    ----------
    grouper : AssignmentGrouper
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

    Assume the gradebook has assignments named `homework 01`, `homework 01 -
    programming`, `homework 02`, `homework 02 - programming`, etc., the
    following will "combine" the assignments into `homework 01`, `homework 02`,
    etc. In order to unify the programming parts with the rest of the homework,
    we can write:

    >>> gradebook.combine_assignment_parts(lambda s: s.split('-')[0].strip())

    This used a callable grouper. Alternatively, one could use a list of prefixes:

    >>> gradebook.combine_assignment_parts(["homework 01", "homework 02"])

    Or a dictionary mapping new assignment names to their parts:

    >>> gradebook.combine_assignment_parts({
    ... 'homework 01': {'homework 01', 'homework 01 - programming'},
    ... 'homework 02': {'homework 02', 'homework 02 - programming'}
    ... })


    """
    dct = resolve_assignment_grouper(grouper, gb.assignments)

    for key, value in dct.items():
        _combine_assignment_parts(gb, key, value)

    gb.grading_groups = {}


# combine_assignment_versions ----------------------------------------------------------


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


def combine_assignment_versions(gb, grouper: AssignmentGrouper):
    """Combine the assignment versions into one single assignment with the new name.

    Sometimes assignments may have several versions which are recorded separately
    in the grading software. For instance, multiple versions of a midterm may be
    distributed to mitigate cheating.

    The individual assignment versions are removed from the gradebook and
    are unified into a single new version.

    It is assumed that all assignment versions have the same number of
    points possible. If this is not the case, a `ValueError` is raised.

    Similarly, it is assumed that no student earns points for more than one
    of the versions. If this is not true, a `ValueError` is raised.

    It is unclear what the result should be if any of the assignments to be
    unified is dropped or is late, but other parts are not. If either of these
    assumptions are violated, this method will raise a `ValueError`.

    Assignment groups are automatically reset to prevent errors. It is
    suggested that the gradebook's assignments be finalized before setting
    the assignment groups.

    Parameters
    ----------
    grouper : AssignmentGrouper
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
    dct = resolve_assignment_grouper(grouper, gb.assignments)

    for key, value in dct.items():
        _combine_assignment_versions(gb, key, value)
