Reviewing and Distributing Grades
=================================

Overviews
---------

`gradelib` provides several functions for reviewing and distributing grades.

First is :func:`gradelib.overview`, which is only available when working in a Jupyter
notebook. It provides a summary of the grades for each student, including an interactive
visualization of the grade distribution that shows the cutoffs for each letter
grade. If called with a student's name as the second argument,
:func:`gradelib.overview` will also display a breakdown of the that student's
grades by assignment.

Statistics
----------

The :mod:`gradelib.statistics` module contains functions for computing various
summaries of the grade distribution, such as
:func:`gradelib.statistics.average_gpa` and :func:`gradelib.statistics.rank`
(which computes the rank of each student in the class).

LaTeX Grade Reports
-------------------

You can generate LaTeX grade reports for each student using the
:func:`gradelib.reports.generate_latex` function. The report contains an
explanation of the student's grade, along with grading notes that clarify any
exceptions, penalties, etc. These notes are automatically added by the
policies in :mod:`gradelib.policies`.
