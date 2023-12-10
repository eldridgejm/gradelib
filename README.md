gradelib
========

![Master](https://github.com/eldridgejm/gradelib/workflows/Test/badge.svg)

`gradelib` is a Python package for computing overall grades. It implements
common grading policies and flexibly supports creative grading schemes. It aims
to make grading straightforward, reproducible, and error-free.
See the documentation at https://eldridgejm.github.io/gradelib/.

Features
--------

* Read grades from common learning management software, including Gradescope
  and Canvas.
* Manage multi-part or multi-version assignments.
* Apply common policies, like dropping the lowest homework and penalizing late assignments.
* Keep track of exceptions, like forgiven late assignments.
* Find "robust" letter grade scales, where no student is too close to a cutoff.
* Display interactive summaries of the grade distribution.
* Make a PDF grade report for each student in the class, explaining their grade.


Example
-------

The following example shows the complete workflow for calculating final grades
in a typical scenario. In this case, some grades were kept on Canvas, while
others were kept on Gradescope. The grading policy allowed for 3 late
assignments between homeworks and labs, as well as one dropped homework and one
dropped lab.


```python
import gradelib
from gradelib.policies import exceptions, lates, drops

# combine grades from Gradescope and Canvas
gb = gradelib.combine_gradebooks([
    gradelib.io.gradescope.read('./gradescope.csv'),
    gradelib.io.canvas.read('./canvas.csv')
])

HOMEWORKS = gb.assignments.starting_with("home")
LABS = gb.assignments.starting_with("lab")

# group the assignments and determine their weight in the overall score calculation
gb.grading_groups = {
    'homeworks': (HOMEWORKS, .25),
    'labs': (LABS, .25),
    'midterm exam': .25,
    'final exam': .25
}

# handle exceptions
exceptions.make_exceptions(
    gb,
    "Justin",
    [
        exceptions.Drop("lab 01", reason="illness"),
        exceptions.Replace("homework 01", with_="homework 02", reason="added late")
    ]
)

# apply grading policies
lates.penalize(gb, policy=lates.Forgive(3), within=HOMEWORKS + LABS)
drops.drop_most_favorable(gb, 1, within=HOMEWORKS)
drops.drop_most_favorable(gb, 1, within=LABS)

# find robust letter grade cutoffs by clustering grades
gb.scale = gradelib.scales.find_robust_scale(gb.overall_score)

# generate student reports, complete with auto-generated grading notes about which
# assignments were dropped, penalized for being late, etc.
gradelib.reports.generate_latex(gb, output_directory=".")
```

The final grading scale was determined by a simple clustering algorithm which
finds "robust" thresholds for every letter grade. These are thresholds which
are far from the nearest grade on the left; that is, there are no students "on
the cusp" of the next highest letter grade.

Finally, if we're working in a Jupyter notebook, we can plot an interactive overview of the grade distribution:

```python
gradelib.overview(gb)
```

Documentation
-------------

The full documentation is at https://eldridgejm.github.io/gradelib/.
