import numpy as np

import bokeh.models
import bokeh.plotting
import bokeh.io

from .statistics import outcomes, letter_grade_distribution
from ._util import in_jupyter_notebook
from .core import Gradebook

# grade_distribution -------------------------------------------------------------------


def _plot_grade_distribution_histogram(
    fig: bokeh.plotting.figure, x_hist: np.ndarray, y_hist: np.ndarray
):
    fig.quad(top=y_hist, bottom=0, left=x_hist[:-1], right=x_hist[1:], fill_alpha=0.7)


def _plot_grade_distribution_students(
    fig: bokeh.plotting.figure, gb: Gradebook
) -> bokeh.models.GlyphRenderer:
    source_df = outcomes(gb).reset_index().rename(columns={"index": "student"})
    source_df["student"] = source_df["student"].astype(str)

    source = bokeh.models.ColumnDataSource(source_df)

    return fig.scatter(
        "overall score",
        0.05,
        source=source,
        color="black",
        size=10,
        fill_alpha=0.2,
        marker="triangle",
    )


def _plot_grade_distribution_hover_tool(
    fig: bokeh.plotting.figure, renderer: bokeh.models.GlyphRenderer
):
    fig.hover.tooltips = [
        ("student", "@student"),
        ("overall score", "@{overall score}"),
        ("letter grade", "@{letter}"),
        ("rank", "@{rank}"),
        ("percentile", "@{percentile}"),
    ]
    fig.hover.renderers = [renderer]


def _plot_grade_distribution_thresholds(
    fig: bokeh.plotting.figure, gb: Gradebook, y_max: float
):
    # plot threshold lines
    for letter, threshold in gb.scale.items():
        fig.line(threshold, [0, y_max], line_dash="dashed", color="black")

    # set up the ticker
    fig.xaxis.ticker = list(gb.scale.values())

    # change the major labels
    lgd = letter_grade_distribution(gb.letter_grades)
    for letter, threshold in gb.scale.items():
        count = f"({lgd[letter]})"
        pct = f"{threshold * 100:0.1f}%"
        fig.xaxis.major_label_overrides[
            threshold
        ] = f"{pct}\n{letter}\n{count}"  # pyright: ignore

    fig.xaxis.major_label_text_font_size = "14px"
    fig.grid.visible = False


def grade_distribution(
    gradebook: Gradebook, x_min: float = 0.6, x_max: float = 1, bin_width: float = 0.025
):
    """Visualize the grade distribution with respect to a scale.

    This will plot an interactive histogram of the grade distribution, with
    each individual grade marked as a dot. Furthermore, if a gradine scale is
    provided, the letter grade thresholds are marked on the histogram as
    vertical lines, and the frequency of each letter grade is shown.

    Parameters
    ----------
    gradebook : Gradebook
    x_min : float
        The smallest extent of the axis containing scores. Default: 0.6
    x_max : float
        The greatest extent of the axis containing scores. Default: 1.02
    bin_width
        How wide each bin should be. Default: 0.025.

    """
    if in_jupyter_notebook():
        bokeh.io.output_notebook()

    # compute a histogram of overall scores
    # x_hist is the bin edges, y_hist is the bin counts
    y_hist, x_hist = np.histogram(
        gradebook.overall_score, bins=np.arange(x_min, x_max, bin_width)
    )

    # give a little headroom above the plot
    y_max = max(y_hist) * 1.1

    # create the base figure
    fig = bokeh.plotting.figure(
        title="Grade Distribution",
        plot_width=800,
        plot_height=400,
        x_range=[x_min, x_max],
        y_range=[0, y_max],
        tools="hover,pan,box_zoom,save,reset,help",
        y_axis_label="Count",
    )

    _plot_grade_distribution_histogram(fig, x_hist, y_hist)
    renderer = _plot_grade_distribution_students(fig, gradebook)
    _plot_grade_distribution_hover_tool(fig, renderer)
    _plot_grade_distribution_thresholds(fig, gradebook, y_max)

    bokeh.plotting.show(fig)
