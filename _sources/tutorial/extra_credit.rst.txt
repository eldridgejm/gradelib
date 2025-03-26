Extra Credit
============

`gradelib` supports robustly supports different strategies for providing extra credit.
There are two main approaches to giving extra credit in `gradelib`:

1. Extra credit within an assignment, allowing its score to be above 100%. This is permitted
   by default.
2. Extra credit assignments, which can either be part of a grading group with regular assignments,
   or in a separate grading group.


These approaches are not mutually exclusive, and can be combined in a single gradebook.
They are described below.

Within assignments
------------------

Allowing extra credit within an assignment is simple: `gradelib` assumes that
assignment scores can be above 100% and functions accordingly. If you wish to
disallow assignment scores above 100%, it's usually easy to do so by
reconfiguring your gradebook application (e.g., Canvas) before exporting grades
to `gradelib`.

If you allow extra credit within assignments, grading group scores can potentially
exceed 100%. This is not a problem for `gradelib`, which will calculate the overall
grade as the sum of the weighted scores of the grading groups. However, if you wish
to cap the grading group scores at 100%, you can do so when creating grading groups.

For example, suppose extra credit is allowed on homeworks, so that a student can earn
above 100% on a homework assignment. To cap the homework group score at 100%, you can
create the grading group using the ``cap_total_score_at_100_percent`` parameter:

.. testsetup::

    import gradelib
    import pandas as pd

.. testcode::

    # create a gradebook; notice that student A1 earned above 100% on hw01
    columns = ["exam", "hw01", "hw02"]
    p1 = pd.Series(data=[10, 60, 100], index=columns, name="A1")
    p2 = pd.Series(data=[8, 7, 15], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([10, 50, 100], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    gradebook.grading_groups = {
        "homeworks": gradelib.GradingGroup(
            {
                "hw01": 0.5,
                "hw02": 0.5,
            },
            group_weight=0.5,
            cap_total_score_at_100_percent=True
        ),
        "exam": 0.5
    }

    print("A1's Homework 01 score:", gradebook.score.loc["A1", "hw01"])
    print("A1's overall homework group score:", gradebook.grading_group_scores.loc["A1", "homeworks"])
    print("A1's overall score in the class:", gradebook.overall_score.loc["A1"])

This outputs:

.. testoutput::

    A1's Homework 01 score: 1.2
    A1's overall homework group score: 1.0
    A1's overall score in the class: 1.0



Extra credit assignments
------------------------

Extra credit assignments can either be within a grading group containing regular assignments,
or in their own grading group.

Within a regular grading group
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create an extra credit assignment within a group containing regular (non-extra credit)
assignments, create the grading group as usual, but wrap the weight of the extra
credit assignment in :class:`~gradelib.ExtraCredit`. For example, suppose you have
a group of homework assignments, and you want to add an extra credit assignment
to the group worth 10\% of the homework group score. You can do this as follows:

.. testcode::

    # create a gradebook with an extra credit assignment
    columns = ["extra credit", "hw01", "hw02"]
    p1 = pd.Series(data=[10, 50, 100], index=columns, name="A1")
    p2 = pd.Series(data=[8, 7, 15], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([10, 50, 100], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    gradebook.grading_groups = {
        "homeworks": gradelib.GradingGroup(
            {
                "hw01": 0.5,
                "hw02": 0.5,
                "extra credit": gradelib.ExtraCredit(0.1)
            },
            group_weight=1,
        ),
    }

    print("A1's overall homework group score:", gradebook.grading_group_scores.loc["A1", "homeworks"])

.. testoutput::

    A1's overall homework group score: 1.1

Extra credit assignments within a group affect a student's score within the group, but
they do not count towards the points possible within a group.

To make it more convenient to define extra credit assignments, `gradelib` provides
the :meth:`~gradelib.GradingGroup.with_extra_credit_assignments` method. This method takes an
existing grading group and adds extra credit assignments to it. With this approach, the
above example becomes:

.. testcode::

    # create a gradebook with an extra credit assignment
    columns = ["extra credit", "hw01", "hw02"]
    p1 = pd.Series(data=[10, 50, 100], index=columns, name="A1")
    p2 = pd.Series(data=[8, 7, 15], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([10, 50, 100], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    gradebook.grading_groups = {
        "homeworks": gradelib.GradingGroup.with_equal_weights(
            gradebook.assignments.starting_with("hw"),
            group_weight=1
        ).with_extra_credit_assignments({"extra credit": 0.1}),
    }

    print("A1's overall homework group score:", gradebook.grading_group_scores.loc["A1", "homeworks"])

.. testoutput::

    A1's overall homework group score: 1.1

Within a separate grading group
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create a grading group made up entirely of extra credit, wrap the grading group's
weight in :class:`~gradelib.ExtraCredit` when creating it. For example, suppose you have
a group of extra credit assignments worth 10\% of the overall grade. You can create
this group as follows:

.. testcode::

    # create a gradebook with an extra credit assignment
    columns = ["extra credit 1", "extra credit 2", "exam"]
    p1 = pd.Series(data=[10, 100, 20], index=columns, name="A1")
    p2 = pd.Series(data=[8, 15, 20], index=columns, name="A2")
    points_earned = pd.DataFrame([p1, p2])
    points_possible = pd.Series([10, 100, 20], index=columns)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

    gradebook.grading_groups = {
        "extra credit": gradelib.GradingGroup.with_proportional_weights(
            gradebook,
            gradebook.assignments.starting_with("extra credit"),
            group_weight=gradelib.ExtraCredit(0.1)
        ),
        "exam": 1
    }

    print("A1's overall extra credit group score:", gradebook.grading_group_scores.loc["A1", "extra credit"])
    print("A1's overall score in the class:", gradebook.overall_score.loc["A1"])

This produces:

.. testoutput::

    A1's overall extra credit group score: 1.0
    A1's overall score in the class: 1.1

.. note::

   When creating an extra credit grading group, the assignments within the group are
   treated as regular assignments because they should contribute to the total points possible
   for the group. That is, :meth:`~gradelib.GradingGroup.with_extra_credit_assignments` is not
   used to add assignments to an extra credit grading group.
