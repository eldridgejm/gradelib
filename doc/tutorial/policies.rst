Grading Policies
================

Common grading policies are implemented in `gradelib` as functions that modify
the core data attributes of a :class:`Gradebook`. You can find these in the
:mod:`gradelib.policies` module.

Handling late assignments
-------------------------

The :func:`gradelib.policies.lates.penalize` function penalizes late
assignments. Its implementation is very flexible, and allows you to specify
creative late policies.


For example, suppose we have the following grades:

.. testsetup::

   import gradelib._examples
   gradebook = gradelib._examples.with_lates()

.. doctest::

   >>> gradebook.points_earned
             Homework 01  Homework 02  Homework 03
   <Justin>          7.0          5.0          9.0
   <Barack>         10.0          8.0          7.0

Some of the assignments have been turned in late:

.. doctest::

   >>> gradebook.late
           Homework 01  Homework 02  Homework 03
   Justin         True         True         True
   Barack         True        False        False

By default, the :func:`gradelib.policies.lates.penalize` function will penalize
late assignments by giving them zero points (a 100% deduction):

.. testsetup:: penalize-all

   import gradelib._examples
   gradebook = gradelib._examples.with_lates()

.. doctest:: penalize-all

   >>> gradelib.policies.lates.penalize(gradebook)
   >>> gradebook.points_earned
             Homework 01  Homework 02  Homework 03
   <Justin>          0.0          0.0          0.0
   <Barack>          0.0          8.0          7.0

.. testsetup:: penalize-50

   import gradelib._examples
   gradebook = gradelib._examples.with_lates()

If we want to deduct a different percentage, we can specify that as an
argument:

.. doctest:: penalize-50

   >>> from gradelib import Percentage
   >>> from gradelib.policies.lates import Deduct
   >>> gradelib.policies.lates.penalize(gradebook, policy=Deduct(Percentage(50)))
   >>> gradebook.points_earned
             Homework 01  Homework 02  Homework 03
   <Justin>          3.5          2.5          4.5
   <Barack>          5.0          8.0          7.0

A common policy is to forgive a certain number of late assignments. For example,
we might want to forgive the first two late assignments, but penalize all subsequent
lates. We can do this with :class:`gradelib.policies.lates.Forgive`:

.. testsetup:: forgive-2

   import gradelib._examples
   gradebook = gradelib._examples.with_lates()

.. doctest:: forgive-2

    >>> from gradelib.policies.lates import Forgive
    >>> gradelib.policies.lates.penalize(gradebook, policy=Forgive(2))
    >>> gradebook.points_earned
              Homework 01  Homework 02  Homework 03
    <Justin>          7.0          5.0          0.0
    <Barack>         10.0          8.0          7.0

Notice how Justin's third assignment was penalized, but his first two were not.

The ``policy`` argument to :func:`gradelib.policies.lates.penalize` can be used
to specify very creative late policies. It accepts a callable that takes a
:class:`gradelib.policies.lates.LateInfo` object describing a late assignment
and returns a :class:`gradelib.Points` or :class:`gradelib.Percentage` object
specifying the deduction for that late.

For example, suppose we want to penalize late assignments by 10% for each hour
they are late, up to a maximum of 50%. We can do this with the following
function:

.. testsetup:: penalize-10-per-hour

   import gradelib._examples
   gradebook = gradelib._examples.with_lates()

.. doctest:: penalize-10-per-hour

    >>> from gradelib import Percentage
    >>> def penalize_10_per_hour(late_info):
    ...     seconds_late = late_info.gradebook.lateness.loc[
    ...         late_info.student, late_info.assignment
    ...     ].seconds
    ...     hours_late = seconds_late / 3600
    ...     return Percentage(min(50, 10 * hours_late))
    >>> gradelib.policies.lates.penalize(gradebook, policy=penalize_10_per_hour)

Dropping low scores
-------------------

Another common grading policy is to drop the lowest score in a category. This
can be done in `gradelib` with the
:func:`gradelib.policies.drops.drop_most_favorable` function. Note that
dropping the lowest score in a category is not necessarily the most favorable
to the student, and this function instead finds the assignment that will
increase their overall score the most.

Giving multiple chances at an assignment
----------------------------------------

The :func:`gradelib.policies.attempts.take_best`
function allows you to give students multiple chances at an assignment. By
default, it takes the maximum score of all attempts, but you can specify a
penalty strategy that penalizes multiple attempts.

For example, to penalize each attempt by 10%, you can do the following:


.. testsetup:: take-best

    import pandas as pd
    import gradelib
    import numpy as np

    students = ["Alice", "Barack", "Charlie"]
    assignments = ["Exam - Attempt 01", "Exam - Attempt 02", "Exam - Attempt 03"]
    points_earned = pd.DataFrame(
        [[27, np.nan, np.nan], [15, 21, 30], [21, 25.5, np.nan]],
        index=students, columns=assignments
    )
    points_possible = pd.Series([30, 30, 30], index=assignments)
    gradebook = gradelib.Gradebook(points_earned, points_possible)

.. doctest:: take-best

    >>> from gradelib.policies.attempts import take_best
    >>> gradebook.score
               Exam - Attempt 01  Exam - Attempt 02  Exam - Attempt 03
    <Alice>                  0.9                NaN                NaN
    <Barack>                 0.5               0.70                1.0
    <Charlie>                0.7               0.85                NaN
    >>> def penalize_10_per_attempt(scores):
    ...     """Penalize each subsequent attempt by 10% more than the previous."""
    ...     penalties = pd.Series([1.0 - 0.1 * i for i in range(len(scores))], index=scores.index)
    ...     return scores * penalties
    >>> take_best(
    ...     gradebook,
    ...     attempts=gradebook.assignments.group_by(lambda s: s.split(" - ")[0].strip()),
    ...     penalty_strategy=penalize_10_per_attempt
    ... )
    >>> gradebook.score
                Exam
    <Alice>    0.900
    <Barack>   0.800
    <Charlie>  0.765

Controlling lateness for multiple attempts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When combining multiple attempts, you can control how lateness is determined for
the overall assignment using the ``lateness_strategy`` parameter. The lateness
value is a time duration (Timedelta) indicating how late the assignment was turned in.

Three built-in strategies are available:

- ``max_lateness`` (default): The overall lateness is the maximum lateness across
  all attempts. This has the effect of considering the resulting assignment late
  if any attempt is late.

- ``lateness_of_best``: The overall lateness is taken from whichever attempt
  scored the best (after applying any penalty strategy).

- ``min_lateness``: The overall lateness is the minimum lateness across all
  attempts. If any attempt is on-time (lateness = 0), the overall will be
  on-time. Only if all attempts are late will the overall be late, using the
  smallest lateness amount.

Tracking exceptions
-------------------

The :func:`gradelib.policies.exceptions.make_exceptions` function allows you to
make grading exceptions for individual students. It adds notes to the gradebook
that appear in the student's grade summary, making the exception clear to the
student.
