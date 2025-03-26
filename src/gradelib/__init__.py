"""A package for computing overall grades in courses @ UCSD."""

from .core import (
    combine_gradebooks,
    Gradebook,
    GradebookOptions,
    Assignments,
    Student,
    Students,
    Points,
    Percentage,
    GradingGroup,
    ExtraCredit,
)

from . import io
from . import plot
from . import policies
from . import preprocessing
from . import reports
from . import scales
from . import statistics
from . import _util

if _util.in_jupyter_notebook():
    from .overview import overview  # type: ignore

__all__ = [
    "combine_gradebooks",
    "Gradebook",
    "GradebookOptions",
    "Assignments",
    "Student",
    "Students",
    "Points",
    "Percentage",
    "preprocessing",
    "policies",
    "io",
    "plot",
    "reports",
    "GradingGroup",
    "ExtaCredit",
    "statistics",
    "scales",
    "overview",
]
