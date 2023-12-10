Loading Grades
==============

If you use Canvas or Gradescope to manage your course's grades, you can import
them into `gradelib` :class:`Gradebook` objects using the
:mod:`gradelib.io.canvas.read` and :mod:`gradelib.io.gradescope.read`
functions, respectively. These functions accept a CSV exported from the
corresponding service, and return a :class:`Gradebook` object.

Sometimes you'll want to load grades from multiple sources. For example, you
might use Gradescope for homeworks and Canvas for exams. In this case, you can
use the :func:`gradelib.combine_gradebooks` function to merge multiple
:class:`Gradebook` objects into one.
