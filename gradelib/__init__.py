"""A package for computing overall grades in courses @ UCSD."""

from .core import (
    combine_gradebooks,
    normalize,
    Gradebook,
    GradebookOptions,
    Assignments,
    LazyAssignments,
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
    average_gpa,
    letter_grade_distribution,
    plot_grade_distribution,
    find_robust_scale,
)

from . import policies
