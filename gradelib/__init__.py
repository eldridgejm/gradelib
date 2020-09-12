"""A package for computing overall grades in courses @ UCSD."""

from .io import (
    read_egrades_roster,
    read_canvas,
    read_gradescope,
    write_canvas_grades,
    write_egrades,
)
from .gradebook import Gradebook, Assignments
from .scales import (
    DEFAULT_SCALE,
    map_scores_to_letter_grades,
    average_gpa,
    letter_grade_distribution,
    plot_grade_distribution,
    find_robust_scale,
)
