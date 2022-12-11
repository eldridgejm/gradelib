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

.. autoclass:: AssignmentGroup
   :members:

.. autoclass:: Assignments
   :members:

.. autoclass:: Student
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

:mod:`scales`
==============

.. module:: scales

   Grading scales.
