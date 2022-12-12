import numpy as np

from bokeh.models import ColumnDataSource
from bokeh.plotting import figure, show
from bokeh.io import output_notebook

from .summarize import rank, percentile, outcomes, letter_grade_distribution
from ._common import in_jupyter_notebook

# grade_distribution -------------------------------------------------------------------

def _plot_grade_distribution_histogram(p, x_hist, y_hist):
    p.quad(top=y_hist, bottom=0, left=x_hist[:-1], right=x_hist[1:], fill_alpha=0.7)


def _plot_grade_distribution_students(p, gb):
    source_df = outcomes(gb).reset_index().rename(columns={"index": "student"})
    source_df["student"] = source_df["student"].astype(str)

    source = ColumnDataSource(source_df)

    return p.scatter(
        "overall score",
        0.05,
        source=source,
        color="black",
        size=10,
        fill_alpha=0.2,
        marker="triangle",
    )

def _plot_grade_distribution_hover_tool(p, r):
    p.hover.tooltips = [
        ("student", "@student"),
        ("overall score", "@{overall score}"),
        ("letter grade", "@{letter}"),
        ("rank", "@{rank}"),
        ("percentile", "@{percentile}"),
    ]
    p.hover.renderers = [r]

def _plot_grade_distribution_thresholds(p, gb, y_max):
    # plot threshold lines
    for letter, threshold in gb.scale.items():
        p.line(threshold, [0, y_max], line_dash="dashed", color="black")

    # set up the ticker
    p.xaxis.ticker = list(gb.scale.values())

    # change the major labels
    lgd = letter_grade_distribution(gb.letter_grades)
    for letter, threshold in gb.scale.items():
        count = f"({lgd[letter]})"
        pct = f"{threshold * 100:0.1f}%"
        p.xaxis.major_label_overrides[threshold] = f'{pct}\n{letter}\n{count}'

    p.xaxis.major_label_text_font_size = "14px"
    p.grid.visible = False


def grade_distribution(
    gb,
    scale=None,
    x_min=0.6,
    x_max=1,
    bin_size=0.025
):
    """Visualize the grade distribution with respect to a scale.

    This will plot a histogram of the grade distribution, with each individual
    grade marked as a dot. Furthermore, if a gradine scale is provided,
    the letter grade thresholds are marked on the histogram as vertical lines,
    and the frequency of each letter grade is shown.

    Parameters
    ----------
    gradebook : Gradebook
    x_min : float
        The smallest extent of the axis containing scores. Default: 0.6
    x_max : float
        The greatest extent of the axis containing scores. Default: 1.02
    bins
        What to pass as the `bins` argument to `np.hist`. Default: "auto"

    """
    if in_jupyter_notebook():
        output_notebook()

    # compute a histogram of overall scores
    y_hist, x_hist = np.histogram(gb.overall_score, bins=np.arange(x_min, x_max, bin_size))

    # give a little headroom above the plot
    y_max = max(y_hist) * 1.1

    # create the base figure
    p = figure(
        title="Grade Distribution",
        plot_width=800,
        plot_height=400,
        x_range=[x_min, x_max],
        y_range=[0, y_max],
        tools="hover,pan,box_zoom,save,reset,help",
        y_axis_label="Count",
    )

    _plot_grade_distribution_histogram(p, x_hist, y_hist)
    r = _plot_grade_distribution_students(p, gb)
    _plot_grade_distribution_hover_tool(p, r)
    _plot_grade_distribution_thresholds(p, gb, y_max)

    show(p)
