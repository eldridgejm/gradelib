***
API
***

.. contents:: Table of Contents

Core
====

.. currentmodule:: gradelib

.. autoclass:: Gradebook
   :members:

.. autoclass:: GradebookOptions
   :members:

.. autoclass:: GradingGroup
   :members:

.. autoclass:: Assignments
   :members:
   :special-members: __add__

.. autoclass:: LazyAssignments
   :members:
   :special-members: __add__,__call__

.. class:: AssignmentSelector

   A type alias defining a way of selecting a collection of assignments. In
   words, an assignment selector is one of:

   1. An :class:`Assignments` object.
   2. A sequence of strings, each being an assignment name.
   3. A callable that takes in an instance of :class:`Assignments` and returns
      an instance of :class:`Assignments`.

   The formal definition is:

   .. code:: python

        AssignmentSelector = typing.Union[
                typing.Callable[["Assignments"], "Assignments"],
                "Assignments",
                typing.Sequence[str]
        ]

.. class:: AssignmentGrouper

   A type alias defining a way of grouping a collection of assignments. In
   words, an assignment selector is one of:

   1. An mapping of group names (strings) to collections of assignment names.
   2. A collection of strings; each is interpreted as a prefix, and all assignments
      with that prefix are grouped together.
   3. A callable that takes in an assignment name (a string) and returns the name of the
      group that the assignment should be placed into.

   The formal definition is:

   .. code:: python

        AssignmentGrouper = typing.Union[
            typing.Mapping[str, typing.Collection[str]],
            typing.Collection[str],
            typing.Callable[[str], str],
        ]

.. autoclass:: Points
   :members:

.. autoclass:: Percentage
   :members:

.. autoclass:: Student
   :members:

.. autoclass:: Students
   :members:

.. autofunction:: combine_gradebooks

.. autofunction:: normalize


:mod:`io.gradescope`
====================

.. module:: io.gradescope

   Functionality for reading grades exported from Gradescope.

.. autofunction:: gradelib.io.gradescope.read

:mod:`io.canvas`
====================

.. module:: io.canvas

   Functionality for reading grades exported from Canvas.

.. autofunction:: gradelib.io.canvas.read

:mod:`preprocessing`
====================

.. module:: preprocessing

   Functionality for preprocessing Gradebooks.

.. autofunction:: gradelib.preprocessing.combine_assignment_parts
.. autofunction:: gradelib.preprocessing.combine_assignment_versions

:mod:`policies`
===============

.. module:: policies

   Functionality for implementing grading policies on Gradebooks.

.. autofunction:: gradelib.policies.drop_lowest
.. autofunction:: gradelib.policies.penalize_lates
.. autofunction:: gradelib.policies.redeem
.. autofunction:: gradelib.policies.make_exceptions
.. autoclass:: gradelib.policies.Drop
.. autoclass:: gradelib.policies.ForgiveLate
.. autoclass:: gradelib.policies.Replace

:mod:`scales`
==============

.. module:: gradelib.scales

   Common grading scales and tools for working with them.

.. autodata:: DEFAULT_SCALE
.. autodata:: ROUNDED_DEFAULT_SCALE
.. autofunction:: map_scores_to_letter_grades
.. autofunction:: find_robust_scale

:mod:`statistics`
================

.. module:: gradelib.statistics

   Functions for summarizing gradebooks.

.. autofunction:: rank
.. autofunction:: percentile
.. autofunction:: average_gpa
.. autofunction:: letter_grade_distribution
.. autofunction:: lates
.. autofunction:: outcomes

:mod:`plot`
================

.. module:: gradelib.plot

   Functions for plotting.

.. autofunction:: grade_distribution

:mod:`overview`
===============

.. module:: overview

.. function:: overview(gradebook: Gradebook, student: Optional[str])

   Display an overview of a gradebook. Only available if in a Jupyter Notebook.

   By default, a class overview is displayed. If a student's name is provided
   as the optional second argument, a student summary is displayed.

:mod:`reports`
==============

.. module:: gradelib.reports

.. autofunction:: generate_latex

:mod:`pipeline`
===============

.. module:: gradelib.pipeline

.. autoclass:: Pipeline
