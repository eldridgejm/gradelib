"""A package for computing overall grades in courses @ UCSD."""

from .core import (
    combine_gradebooks,
    normalize,
    Gradebook,
    GradebookOptions,
    Assignments,
    AssignmentSelector,
    AssignmentGrouper,
    Student,
    Students,
    Points,
    Percentage,
    GradingGroup,
)

from .scales import (
    DEFAULT_SCALE,
    ROUNDED_DEFAULT_SCALE,
    map_scores_to_letter_grades,
    find_robust_scale,
)

from .pipeline import Pipeline

from . import preprocessing
from . import policies
from . import summarize
from . import io
from . import plot
from . import reports

from . import _common

if _common.in_jupyter_notebook():
    from .overview import overview

__all__ = [
    "combine_gradebooks",
    "normalize",
    "Gradebook",
    "GradebookOptions",
    "Assignments",
    "AssignmentSelector",
    "AssignmentGrouper",
    "Student",
    "Students",
    "Points",
    "Percentage",
    "DEFAULT_SCALE",
    "ROUNDED_DEFAULT_SCALE",
    "map_scores_to_letter_grades",
    "find_robust_scale",
    "Pipeline",
    "preprocessing",
    "policies",
    "summarize",
    "io",
    "plot",
    "reports",
    "GradingGroup",
    "overview",
]
