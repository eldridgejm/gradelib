Gradebooks
==========

The main object in `gradelib` is the :class:`Gradebook`. It stores all of the
data about a course's grades, and provides basic methods for manipulating that
data.

You normally don't need to create a :class:`Gradebook` from scratch; instead,
you will typically import grades from Gradescope or Canvas using one of the
function described in the next section. But it can be useful to know a little
about how the :class:`Gradebook` is structured, in order to have a sense of how
`gradelib` works, and in case you want to implement a grading strategy that
isn't in this package.

You can think of a :class:`Gradebook` as being comprised of four "core" pieces
of information:

- :attr:`Gradebook.points_earned` is a `pandas` `DataFrame` containing
  the points earned by each student on each assignment.
- :attr:`Gradebook.points_possible` is a `pandas` `Series` containing the number
  of points possible on each assignment.
- :attr:`Gradebook.lateness` is a `pandas` `DataFrame` measuring how late
  each student's submission was for each assignment.
- :attr:`Gradebook.dropped` is a `pandas` `DataFrame` indicating whether
  a student's submission was dropped for a given assignment.

These four attributes contain all of the information about a student's
performance on each assignment. Together with a fifth attribute,
:attr:`Gradebook.grading_groups`, which determines how the assignments should
be grouped together for grading purposes, these are sufficient to compute a
student's overall grade in the course.

Beyond the "core" data attributes above, a :class:`Gradebook` also contains
many "derived" attributes, which are computed from the core data. For example,
:attr:`Gradebook.score` is a `pandas` `DataFrame` containing the score earned
by each student on each assignment, which is computed by dividing
:attr:`Gradebook.points_earned` by :attr:`Gradebook.points_possible`. The
derived attributes are all computed dynamically from the core data.

In `gradelib`, the grading process amounts to starting with a "raw" gradebook
and making a sequence of modifications to the core attributes that reflect the
course's grading policies. For example, you might drop the lowest homework
score and penalize late assignments; this is done by modifying the
:attr:`Gradebook.dropped` and :attr:`Gradebook.points_earned` attributes,
respectively. `gradelib` provides a number of functions for making these
modifications without having to worry about the details of how the core data
are structured, but you can also modify the core data directly if you want to
implement a grading policy that isn't supported.
