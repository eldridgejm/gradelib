"""A package for computing overall grades in courses @ UCSD."""

from .core import (
    combine_gradebooks,
    normalize,
    Gradebook,
    GradebookOptions,
    Assignments,
    LazyAssignments,
    AssignmentSelector,
    AssignmentGrouper,
    Student,
    Students,
    Points,
    Percentage,
    AssignmentGroup,
)

from .scales import (
    DEFAULT_SCALE,
    ROUNDED_DEFAULT_SCALE,
    map_scores_to_letter_grades,
    find_robust_scale,
)

from . import policies
from . import summarize

from . import jupyter

if jupyter.in_notebook():
    from .jupyter import overview
