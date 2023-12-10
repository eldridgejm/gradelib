Grading Groups
==============

.. currentmodule:: gradelib

In a typical class, assignments are organized into groups (e.g., "homeworks",
"labs", etc.), and a student's overall score in the course is determined by a
weighted average of their score in each group. This is done in `gradelib` by
setting the ``.grading_groups`` attribute of the :class:`Gradebook` object.

The :attr:`Gradebook.grading_groups` attribute can be set in several different
ways. The value should be a dict mapping group names to *grading group
definitions*. A group definition can be any of the following:

    - A single number. In this case, the group name is treated as an
      assignment name.
    - A tuple of the form ``(assignments, group_weight)``, where
      ``assignments`` is an iterable of assignment names or a dict mapping
      assignment names to weights. If ``assignments`` is an iterable, the
      weights are inferred to be proportional to the points possible for each
      assignment. If ``assignments`` is a dict, the weights are taken directly
      from the dict.
    - A :class:`GradingGroup` instance.

To normalize the weights of assignments (so that they are all weighed the same)
use the :func:`gradelib.normalize` function.

Example
-------

.. testsetup:: grading_groups

    import pandas as pd
    import gradelib
    import numpy as np

    students = ["Alice", "Barack", "Charlie"]
    assignments = ["hw 01", "hw 02", "hw 03", "lab 01", "lab 02", "exam"]
    points_earned = pd.DataFrame(
        np.random.randint(0, 10, size=(len(students), len(assignments))),
        index=students, columns=assignments
    )
    points_possible = pd.Series([10, 10, 10], index=assignments)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

.. doctest:: grading_groups

    >>> gradebook.grading_groups = {
    ...     # list of assignments, followed by group weight. assignment weights
    ...     # are inferred to be proportional to points possible
    ...     "homeworks": (['hw 01', 'hw 02', 'hw 03'], 0.25),
    ...
    ...     # dictionary of assignment weights, followed by group weight.
    ...     "labs": ({"lab 01": .25, "lab 02": .75}, 0.25),
    ...
    ...     # a single number. the key is interpreted as an assignment name,
    ...     # and an assignment group consisting only of that assignment is
    ...     # created.
    ...     "exam": 0.5
    ... }
