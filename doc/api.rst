***
API
***

.. contents:: Table of Contents

Core
====

.. currentmodule:: gradelib

.. autoclass:: Gradebook
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
