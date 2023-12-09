"""A package for computing overall grades in courses @ UCSD."""

from .core import (
    combine_gradebooks,
    normalize,
    Gradebook,
    GradebookOptions,
    Assignments,
    Student,
    Students,
    Points,
    Percentage,
    GradingGroup,
)

from . import io
from . import plot
from . import policies
from . import preprocessing
from . import reports
from . import scales
from . import statistics

__all__ = [
    "combine_gradebooks",
    "normalize",
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
    "statistics",
    "scales",
]

from . import _util

if _util.in_jupyter_notebook():
    from .overview import overview

    __all__.append("overview")
