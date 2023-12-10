Grading policies
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

The :func:`gradelib.policies.retries.retry` function allows you to give
students multiple chances at an assignment. By default, it takes the maximum
score of all attempts, but you can specify a different function to combine
scores with a penalty.

Tracking exceptions
-------------------
