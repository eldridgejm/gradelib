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

    # read grades from canvas and gradescope
    gradescope_grades = gradelib.Gradebook.from_gradescope('gradescope.csv')
    canvas_grades = gradelib.Gradebook.from_canvas('canvas.csv')

    # combine canvas and gradescope grades into a single gradebook, 
    # checking that all enrolled students are accounted for
    gradebook = gradelib.Gradebook.combine(
        [gradescope_grades, canvas_grades], 
        restrict_pids=roster.index
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
    
    # export letter grades in egrades format
    gradelib.write_egrades('roster.csv', 'letter-grades.csv', letters) 


API
===


.. currentmodule:: gradelib

**Gradebooks**

.. autosummary::
    :nosignatures:

    Gradebook
    Gradebook.from_canvas
    Gradebook.from_gradescope
    Gradebook.combine
    Gradebook.add_assignment
    Gradebook.unify_assignments
    Gradebook.assignments
    Gradebook.pids
    Gradebook.drop_lowest
    Gradebook.forgive_lates
    Gradebook.give_equal_weights
    Gradebook.number_of_lates
    Gradebook.keep_assignments
    Gradebook.remove_assignments
    Gradebook.keep_pids
    Gradebook.score
    Gradebook.total

**Assignments**

.. autosummary::
    Assignments
    Assignments.starting_with
    Assignments.containing
    Assignments.group_by

**Grading Scales**

.. autosummary::
    :nosignatures:

    DEFAULT_SCALE
    map_scores_to_letter_grades
    average_gpa
    letter_grade_distribution
    plot_grade_distribution
    find_robust_scale

**I/O**

.. autosummary::
    :nosignatures:

    read_gradescope
    read_canvas
    read_egrades_roster
    write_canvas_grades
    write_egrades


Gradebooks
----------

.. autoclass:: gradelib.Gradebook
    :members:

Assignments
-----------

.. autoclass:: gradelib.Assignments
    :members:


Grading Scales
--------------

.. data:: DEFAULT_SCALE

    The standard grading scale as an OrderedDict. E.g., 93+ is an A, [90, 93)
    is an A-, etc.

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

.. autofunction:: gradelib.read_gradescope
.. autofunction:: gradelib.read_canvas
.. autofunction:: gradelib.read_egrades_roster
.. autofunction:: gradelib.write_canvas_grades
.. autofunction:: gradelib.write_egrades



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
