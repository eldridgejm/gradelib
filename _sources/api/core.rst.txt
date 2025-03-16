.. currentmodule:: gradelib

``gradelib``
============

.. module:: gradelib

Provides the core types and functionality of :mod:`gradelib`.

Core Types
----------

- :class:`~gradelib.Gradebook` - The core data structure for managing grades.
    - :class:`~gradelib.GradebookOptions` - Options for configuring the gradebook.
    - :class:`~gradelib.GradingGroup` - Represents a group of students and their assignments.
- :class:`~gradelib.Assignments` - Represents a sequence of assignments.
- :class:`~gradelib.Student` and :class:`~gradelib.Students` - Types for representing students.
- :class:`~gradelib.Points` and :class:`~gradelib.Percentage` - Types for representing scores.

.. toctree::
   :maxdepth: 1
   :hidden:

   core-gradebook.rst
   core-assignments.rst
   core-students.rst
   core-amounts.rst

Functions
---------

There are two top-level functions:

.. autofunction:: combine_gradebooks
.. autofunction:: normalize
