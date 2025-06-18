Setting Letter Grade Scales
===========================

The grading scale used to convert overall score to a letter grade is determined
by the :attr:`gradelib.Gradebook.scale` attribute. A scale is simply an ordered mapping
from letter grades to thresholds.

If a scale isn't specified, the default
scale (:data:`gradelib.scales.DEFAULT_SCALE`) is used. This is the "standard"
grading scale, where 93-100 is an A, 90-92 is an A-, 87-89 is a B+, etc.
An alternative grading scale that "rounds" grades up is also provided
(:data:`gradelib.scales.ROUND_UP_SCALE`), where 92.5-100 is an A, 89.5-92.4 is
an A-, 86.5-89.4 is a B+, etc.

Sometimes you might want to find a "robust" scale, where no student is "too close"
to a threshold. This can be done with the :func:`gradelib.scales.find_robust_scale`
function.

Finally, sometimes you will want to "override" the scale for a specific student
in order to assign them a different letter grade than the scale would otherwise
prescribe. This can be done with the :attr:`gradelib.Gradebook.letter_grade_overrides`
attribute.
