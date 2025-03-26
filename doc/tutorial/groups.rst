Grading Groups
==============

.. currentmodule:: gradelib

In a typical class, assignments are organized into groups (e.g., "homeworks",
"labs", etc.), and a student's overall score in the course is determined by a
weighted average of their score in each group. Grading groups are defined in
`gradelib` by setting the ``.grading_groups`` attribute on a :class:`Gradebook`
object. `gradelib` provides several ways to define grading groups conveniently, outlined
below.


To motivate the discussion, let's consider an example. Let's say we have a class with
four types of assignments: homeworks, labs, quizzes, and an exam. The grading scheme
is as follows:

- **Homeworks** are worth 25% of the overall grade. Each homework is weight according
  to the number of points possible: 20% for Homework 01, 30% for Homework 02, and
  50% for Homework 03.
- **Labs** are worth 25% of the overall grade. Each of the three labs is worth 1/3 of
  the lab grade.
- **Quizzes** are worth 30% of the overall grade. Quiz 01 is worth 40% of the quiz
  grade, and Quiz 02 is worth 60%.
- The **exam** is worth 20% of the overall grade.


General approach
----------------

Most generally, the `.grading_groups` attribute should be set to a dictionary
mapping group names to :class:`GradingGroup` objects. The :class:`GradingGroup`
objects define the assignments in the group and their weights, as well as the
weight of the group in the overall grade calculation.

The example scheme can be defined as follows:

.. code-block:: python

    gradebook.grading_groups = {
        "homeworks": gradelib.GradingGroup(
            {
                "Homework 01": 0.2,
                "Homework 02": 0.3,
                "Homework 03": 0.5
            },
            group_weight=0.25
        ),
        "labs": gradelib.GradingGroup(
            {
                "Lab 01": 1/3,
                "Lab 02": 1/3,
                "Lab 03": 1/3
            },
            group_weight=0.25
        ),
        "quizzes": gradelib.GradingGroup(
            {
                "Quiz 01": 0.4,
                "Quiz 02": 0.6
            },
            group_weight=0.3
        ),
        "exam": gradelib.GradingGroup(
            {"Exam": 1},
            group_weight=0.2
        )
    }

This approach can be used to define any grading group configuration. However,
`gradelib` provides several conveniences for making common
configurations easier to define.


Conveniences
------------

A common pattern is to create a grading group where each assignment is equally-weighted,
or weighed according to the nuber of points possible. `gradelib` provides two
convenience methods for defining these types of grading groups: :meth:`GradingGroup.with_equal_weights`
and :meth:`GradingGroup.with_proportional_weights`.

To make it easier to define a grading group with only one assignment, the `.grading_groups`
dictionary may contain keys mapped to a single float, which is interpreted as the weight
of the assignment in the overall grade calculation.

Finally, the `.grading_groups` dictionary may also contain keys mapped to a tuple of
two elements: a dictionary of assignment weights, followed by the group weight. This
saves some typing over the general approach.

Altogether, the example scheme can be defined as follows:

.. testsetup:: grading_groups

    import pandas as pd
    import gradelib
    import numpy as np

    students = ["Alice", "Barack", "Charlie"]
    assignments = ["Homework 01", "Homework 02", "Homework 03", "lab 01", "lab 02", "quiz 1", "quiz 2", "exam"]
    points_earned = pd.DataFrame(
        np.random.randint(0, 10, size=(len(students), len(assignments))),
        index=students, columns=assignments
    )
    points_possible = pd.Series([10, 10, 10, 15, 20, 10, 10, 10], index=assignments)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

.. testcode:: grading_groups

    gradebook.grading_groups = {
        # each assignment is given a weight proportional to the
        # number of points possible
        "homeworks": gradelib.GradingGroup.with_proportional_weights(
            gradebook,
            gradebook.assignments.starting_with("Homework"),
            group_weight=0.25
        ),

        # each assignment is equally weighted
        "labs": gradelib.GradingGroup.with_equal_weights(
            gradebook.assignments.starting_with("lab"),
            group_weight=0.25
        ),

        # the 2-tuple format is used to save some typing
        "quizzes": (
            {
                "quiz 1": 0.4,
                "quiz 2": 0.6
            },
            0.3
        ),

        # a single assignment can be given a weight directly without creating
        # a GradingGroup object
        "exam": 0.2
    }
