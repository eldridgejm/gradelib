gradelib
========

gradelib is a python package which streamlines end-of-quarter grading. It is
designed to work with the tools most commonly used at UC San Diego, including
gradescope, canvas, and eGrades.

Features
--------

- read grades from gradescope and canvas
- implement common grading strategies, like dropping the lowest homework and
  forgiving late assignments
- intelligently choose letter grade cutoffs by clustering
- visualize score distributions
- create upload-ready gradebooks for eGrades and canvas

Example
-------

The following example shows the complete workflow for calculating final grades
in a typical scenario. In this case, some grades were kept on Canvas, while
others were kept on Gradescope. The grading policy allowed for 4 late
assignments between homeworks and labs, as well as one dropped homework and one
dropped lab. The final grading scale is determined by a simple clustering
algorithm which finds "robust" thresholds for every letter grade.


```python
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
```


Documentation
-------------

The full documentation is at https://eldridgejm.github.io/gradelib/.
