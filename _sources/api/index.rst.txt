***
API
***

.. currentmodule:: gradelib

This part of the documentation describes the API for :mod:`gradelib`. The
functionality of the package can be organized into two categories: **Computing
Grades** and **Reviewing Grades**.

Computing Grades
================

- :mod:`gradelib` - Core types, such as :class:`Gradebook` and :class:`Student`.
- :mod:`gradelib.preprocessing` - Preprocessing gradebooks.
- :mod:`gradelib.io` - Reading and writing grades.
- :mod:`gradelib.policies` - Common grading policies, like lates, drops, and exceptions.
- :mod:`gradelib.scales` - Letter grade scales.

.. toctree::
   :maxdepth: 1
   :hidden:

   core.rst
   io.rst
   preprocessing.rst
   policies.rst
   scales.rst

Reviewing Grades
================

- :mod:`gradelib.statistics` - Summary statistics for computed grades.
- :mod:`gradelib.plot` - Display visual summaries.
- :mod:`gradelib.overview` - Interactive overview of grades.
- :mod:`gradelib.reports` - LaTeX grade reports.

.. toctree::
   :maxdepth: 1
   :hidden:

   statistics.rst
   plot.rst
   overview.rst
   reports.rst
