.. gradelib documentation master file, created by
   sphinx-quickstart on Thu Sep 10 23:17:58 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

gradelib
========

gradelib is a python library that streamlines end-of-quarter grading.
It is designed to work with the common tools used at UC San Diego, including
gradescope, canvas, and eGrades.


Workflow
========

The following example shows the complete workflow for calculating final grades
in a typical scenario. In this case, some grades were kept on Canvas, while
others were kept on Gradescope. The grading policy allowed for 4 late
assignments between homeworks and labs, as well as one dropped homework and one
dropped lab. The final grading scale is determined by a simple clustering
algorithm which finds "robust" thresholds for every letter grade.

.. code:: python

    import gradelib

    # read the egrades roster
    roster = gradelib.read_egrades_roster('roster.csv')

    # read grades from canvas
    canvas_grades = gradelib.Gradebook.from_canvas('canvas.csv')

    # read grades from gradescope
    # note: Gradescope is inconsistent with time of submission, sometimes showing
    # that an assignment is on-time in the web interface, but a minute or so late
    # in the exported CSV. `from_gradescope` has a default fudge-factor that
    # is meant to account for this; see the documentation for more details.
    gradescope_grades = gradelib.Gradebook.from_gradescope('gradescope.csv')

    # combine canvas and gradescope grades into a single gradebook,
    # checking that all enrolled students are accounted for
    gradebook = gradelib.Gradebook.combine(
        [gradescope_grades, canvas_grades],
        restrict_to_pids=roster.index
    )

    # define assignment groups
    HOMEWORKS = gradebook.assignments.starting_with('home')
    LABS = gradebook.assignments.starting_with('lab')

    # apply grading policy
    gradebook = (
        gradebook
        .forgive_lates(4, within=HOMEWORKS + LABS)
        .drop_lowest(1, within=HOMEWORKS)
        .drop_lowest(1, within=LABS)
    )

    # calculate overall grades according to weighted grading
    # scheme; 25% homeworks, 20% labs, etc.
    overall = (
        .25 * gradebook.score(HOMEWORKS)
        +
        .20 * gradebook.score(LABS)
        +
        .05 * gradebook.score('project 01')
        +
        .10 * gradebook.score('project 02')
        +
        .10 * gradebook.score('midterm exam')
        +
        .30 * gradebook.score('final exam')
    )

    # find robust letter grade cutoffs by clustering grades
    robust_scale = gradelib.find_robust_scale(overall)

    # visualize the grade distribution
    gradelib.plot_grade_distribution(overall, robust_scale)

    # assign letter grades
    letters = gradelib.map_scores_to_letter_grades(overall, robust_scale)


API
===

.. currentmodule:: gradelib

**Gradebook**

.. autosummary::
    :nosignatures:

    Gradebook
    Gradebook.assignments
    Gradebook.pids
    Gradebook.score
    Gradebook.add_assignment
    Gradebook.restrict_to_assignments
    Gradebook.remove_assignments
    Gradebook.combine_assignment_parts
    Gradebook.combine_assignment_versions
    Gradebook.restrict_to_pids
    combine_gradebooks

**Assignments**

.. autosummary::
    Assignments
    Assignments.starting_with
    Assignments.containing
    Assignments.group_by

**Student**

.. autosummary::
    Student

:mod:`gradelib.scales` -- **grading scales**

.. autosummary::
    :nosignatures:

    DEFAULT_SCALE
    ROUNDED_DEFAULT_SCALE
    map_scores_to_letter_grades
    average_gpa
    letter_grade_distribution
    plot_grade_distribution
    find_robust_scale

**I/O**

.. autosummary::
    :nosignatures:

    io.gradescope.read


Gradebooks
----------

.. autoclass:: gradelib.Gradebook
    :members:

.. autoclass:: gradelib.GradebookOptions
    :members:

.. autoclass:: gradelib.AssignmentGroup
    :members:

.. autofunction:: gradelib.combine_gradebooks
.. autofunction:: gradelib.normalize

Assignments
-----------

.. autoclass:: gradelib.Assignments
    :members:

Student
-------

.. autoclass:: gradelib.Student
    :members:

Grading Scales
--------------

.. data:: DEFAULT_SCALE

    The standard grading scale as an OrderedDict. E.g., 93+ is an A, [90, 93)
    is an A-, etc.

.. data:: ROUNDED_DEFAULT_SCALE

    A rounded version of the default scale in which each threshold is one half point lower.

.. autofunction:: map_scores_to_letter_grades
.. autofunction:: average_gpa
.. autofunction:: letter_grade_distribution
.. autofunction:: plot_grade_distribution
.. autofunction:: find_robust_scale

.. toctree::
   :maxdepth: 2
   :caption: Contents:


I/O
---

.. autofunction:: gradelib.io.gradescope.read



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
