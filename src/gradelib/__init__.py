# ruff: noqa: I001
"""A package for computing overall grades in courses @ UCSD."""

from .core import (
    Assignments,
    ExtraCredit,
    Gradebook,
    GradebookOptions,
    GradingGroup,
    Percentage,
    Points,
    Student,
    Students,
    combine_gradebooks,
)
from . import _util, io, plot, policies, preprocessing, reports, scales, statistics

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
    "ExtraCredit",
    "statistics",
    "scales",
    "overview",
]
