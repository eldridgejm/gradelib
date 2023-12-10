Preprocessing
=============

Once you have loaded your grades into a :class:`Gradebook`, you might need to
do some "preprocessing" to clean things up. For example, you may have given two
different versions of each exam, represented by two different assignments in
your grading platform that should be combined into one. `gradelib` provides
functions for doing this kind of preprocessing in the :mod:`gradelib.preprocessing`
module.

Combining assignment versions
-----------------------------

Let's say you gave three versions of an exam, which you named "Exam - Version A",
"Exam - Version B", and "Exam - Version C", along with a homework assignment
named "Homework 1":

.. testsetup::

   from gradelib import Gradebook
   import numpy as np
   import pandas as pd

   students = ["Justin", "Barack", "Pat"]
   assignments = ["Exam - Version A", "Exam - Version B", "Exam - Version C", "Homework 1"]

   points_earned = pd.DataFrame(
       [[8, np.nan, np.nan, 4],
        [np.nan, 6, np.nan, 3],
        [np.nan, np.nan, 7, 2]],
       index=students,
       columns=assignments,
   )

   points_possible = pd.Series(
         [10, 10, 10, 5],
         index=assignments,
   )

   gradebook = Gradebook(
       points_earned=points_earned,
       points_possible=points_possible,
   )

.. doctest::

   >>> gradebook.assignments
   Assignments(names=['Exam - Version A', 'Exam - Version B', 'Exam - Version C', 'Homework 1'])

Each student will have a grade for exactly one of the exam versions.
You want to combine the three exam versions into one assignment, "Exam", so that it
contains the exam grade for each student.
You can do this using the :func:`gradelib.preprocessing.combine_assignments`
function, which takes in a gradebook and a dictionary mapping the new
assignment name to a list of the old assignment names that should be combined:

.. doctest::

   >>> from gradelib.preprocessing import combine_assignment_versions
   >>> combine_assignment_versions(gradebook, {
   ...      "Exam": ["Exam - Version A", "Exam - Version B", "Exam - Version C"]
   ... })
   >>> gradebook.assignments
   Assignments(names=['Exam', 'Homework 1'])

Like many functions in `gradelib`, this tries to be safe: if a student has a
grade for more than one of the old assignments, it will raise an error. This is
to prevent you from accidentally combining assignments that shouldn't be
combined.

Instead of typing out the list of old assignment names, you can use convenience
methods on :attr:`Gradebook.assignments` to select them. For example, you can
use :meth:`gradelib.Assignments.starting_with`:

.. doctest::

   >>> from gradelib.preprocessing import combine_assignment_versions
   >>> combine_assignment_versions(gradebook, {
   ...      "Exam": gradebook.assignments.starting_with("Exam")
   ... })
   >>> gradebook.assignments
   Assignments(names=['Exam', 'Homework 1'])

Combining assignment parts
--------------------------

Sometimes an assignment will be split into multiple parts on your grading
platform. For example, you might split your homework into "Homework 01 -
Written Problems", "Homework 01 - Programming Problem 01", "Homework 01 -
Programming Problem 02", so that the students can submit each part separately
(the programming problems each having their own autograder).

To combine these parts into a single assignment (by summing their points),
you can use the :func:`gradelib.preprocessing.combine_assignment_parts`
function.
