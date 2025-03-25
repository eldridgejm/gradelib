from typing import Tuple, Sequence, Optional, Union, Callable
import pathlib

import bokeh.io
import bokeh.models
import bokeh.plotting
import matplotlib.animation
import matplotlib.pyplot as plt
import numpy as np

from .statistics import (
    outcomes as _outcomes,
    letter_grade_distribution as _letter_grade_distribution,
)
from ._util import in_jupyter_notebook as _in_jupyter_notebook
from .core import Gradebook

# grade_distribution -------------------------------------------------------------------


def _plot_grade_distribution_histogram(
    fig: bokeh.models.Model, x_hist: np.ndarray, y_hist: np.ndarray
):
    fig.quad(top=y_hist, bottom=0, left=x_hist[:-1], right=x_hist[1:], fill_alpha=0.7)


def _plot_grade_distribution_students(
    fig: bokeh.models.Model, gb: Gradebook
) -> bokeh.models.GlyphRenderer:
    source_df = _outcomes(gb).reset_index().rename(columns={"index": "student"})
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
    fig: bokeh.models.Model, renderer: bokeh.models.GlyphRenderer
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
    fig: bokeh.models.Model, gb: Gradebook, y_max: float
):
    # plot threshold lines
    for letter, threshold in gb.scale.items():
        fig.line(threshold, [0, y_max], line_dash="dashed", color="black")

    # set up the ticker
    fig.xaxis.ticker = list(gb.scale.values())

    # change the major labels
    lgd = _letter_grade_distribution(gb.letter_grades)
    for letter, threshold in gb.scale.items():
        count = f"({lgd[letter]})"
        pct = f"{threshold * 100:0.1f}%"
        fig.xaxis.major_label_overrides[threshold] = f"{pct}\n{letter}\n{count}"  # pyright: ignore

    fig.xaxis.major_label_text_font_size = "14px"
    fig.grid.visible = False


def grade_distribution(
    gradebook: Gradebook, x_min: float = 0.6, x_max: float = 1, bin_width: float = 0.025
):
    """Visualize the grade distribution with respect to a scale.

    This will plot an interactive histogram of the grade distribution, with
    each individual grade marked as a dot. Furthermore, if a grading scale is
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
    if _in_jupyter_notebook():
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
        min_width=800,
        min_height=400,
        x_range=[x_min, x_max],
        y_range=[0, y_max],
        tools="hover,pan,box_zoom,save,reset,help",
        y_axis_label="Count",
    )

    _plot_grade_distribution_histogram(fig, x_hist, y_hist)
    renderer = _plot_grade_distribution_students(fig, gradebook)
    _plot_grade_distribution_hover_tool(fig, renderer)
    _plot_grade_distribution_thresholds(fig, gradebook, y_max)

    bokeh.plotting.show(fig)  # pyright: ignore


# grade_shift_animation_2d -------------------------------------------------------------


def _grade_shift_animation_2d_setup_figure():
    plt.figure(figsize=(4, 4))
    fig, ax = plt.subplots()

    ax.set_aspect(1)

    ax.set_ylim(0.25, 1.05)
    ax.set_xlim(0.25, 1.05)

    ax.set_xticks([0.3, 1])
    ax.set_yticks([0.3, 1])

    return fig, ax


def grade_shift_animation_2d(
    scores: Tuple[
        Tuple[Sequence[float], Sequence[float]], Tuple[Sequence[float], Sequence[float]]
    ],
    filepath: Optional[Union[str, pathlib.Path]] = None,
    title: Optional[Union[str, tuple[str, str]]] = None,
    xlabel: Optional[Union[str, tuple[str, str]]] = None,
    ylabel: Optional[Union[str, tuple[str, str]]] = None,
    color: str = "#007aff",
    alpha: float = 0.5,
    setup_figure: Optional[Callable] = None,
) -> matplotlib.animation.FuncAnimation:
    """Visualize the shift in scores as an animated scatter plot.

    This is especially useful for visualizing the effect of a grading policy, such as a
    curve or allowing multiple attempts on two assignments. For example, suppose a
    course allows students to retake Midterm 01 and Midterm 02 to improve their scores.
    The animation created by this function will start by plotting a scatter plot of
    Midterm 01 vs. Midterm 02 scores for all students. As the animation progresses, the
    scores will shift to show the new scores after the retake, demonstrating the "shift"
    of the scores due to the grading policy. The animation then "rewinds" to show the
    original scores, allowing for an infinite loop of the before-and-after effect.

    Parameters
    ----------
    scores : Tuple[Tuple[Sequence[float], Sequence[float]], Tuple[Sequence[float], Sequence[float]]]
        A tuple containing two tuples, each with two sequences of floats. The first
        tuple contains the before and after scores for all students on Assignment A,
        and the second tuple contains the before and after scores for all students on
        Assignment B.
    filepath : Optional[Union[str, pathlib.Path]]
        The path to save the animation to. If `None`, the animation will not be saved.
    title : Optional[Union[str, tuple[str, str]]]
        The title of the plot. If a tuple is provided, the first element will be
        displayed at the start of the animation and the second element at the end.
        If a string is provided, it will be used for both the start and end of the animation.
        If nothing is provided, no title will be displayed.
    xlabel : Optional[Union[str, tuple[str, str]]]
        The label for the x-axis. If a tuple is provided, the first element will be
        displayed at the start of the animation and the second element at the end.
        If a string is provided, it will be used for both the start and end of the animation.
        If nothing is provided, no label will be displayed.
    ylabel : Optional[Union[str, tuple[str, str]]]
        The label for the y-axis. If a tuple is provided, the first element will be
        displayed at the start of the animation and the second element at the end.
        If a string is provided, it will be used for both the start and end of the animation.
        If nothing is provided, no label will be displayed.
    color : str
        The color of the points in the scatter plot. Default: "#007aff".
    alpha : float
        The transparency of the points in the scatter plot. Default: 0.5.
    setup_figure : Optional[Callable]
        A callable that sets up the figure and axes for the plot. Should return
        matplotlib Figure and Axes objects. If `None`, a default setup function will be
        used.

    Returns
    -------
    matplotlib.animation.FuncAnimation
        The animation object. If `filepath` is provided, the animation will also be
        saved to the specified path.

    """
    scores_a_before, scores_a_after = scores[0]
    scores_b_before, scores_b_after = scores[1]

    if isinstance(filepath, str):
        filepath = pathlib.Path(filepath)

    if title is not None and isinstance(title, str):
        title = (title, title)

    if xlabel is not None and isinstance(xlabel, str):
        xlabel = (xlabel, xlabel)

    if ylabel is not None and isinstance(ylabel, str):
        ylabel = (ylabel, ylabel)

    if setup_figure is None:
        setup_figure = _grade_shift_animation_2d_setup_figure

    fig, ax = setup_figure()

    if xlabel is not None:
        ax.set_xlabel(xlabel[0])
    if ylabel is not None:
        ax.set_ylabel(ylabel[0])

    if title is not None:
        ax.set_title(title[0])

    scatter = ax.scatter(scores_a_before, scores_b_before, color=color, alpha=alpha)

    start = np.column_stack((scores_a_before, scores_b_before))
    finish = np.column_stack((scores_a_after, scores_b_after))
    delta = finish - start

    n_frames = 300

    def ease_in_out(t, alpha=30):
        """Logistic easing function; smoothes the animation.

        Larger alpha makes the animation "snappier".
        """
        if t < 0.5:
            return (np.tanh((t - 0.25) * alpha) + 1) / 2
        else:
            return 1 - (np.tanh((t - 0.75) * alpha) + 1) / 2

    def interpolate(i):
        return start + delta * ease_in_out(i / n_frames)

    def init():
        return (scatter,)

    def update(i):
        progress = ease_in_out(i / n_frames)
        data = interpolate(i)
        scatter.set_offsets(data)

        if title is not None:
            if progress < 0.5:
                ax.set_title(title[0])
            else:
                ax.set_title(title[1])

        if xlabel is not None:
            if progress < 0.5:
                ax.set_xlabel(xlabel[0])
            else:
                ax.set_xlabel(xlabel[1])

        if ylabel is not None:
            if progress < 0.5:
                ax.set_ylabel(ylabel[0])
            else:
                ax.set_ylabel(ylabel[1])

        return (scatter,)

    animation = matplotlib.animation.FuncAnimation(
        fig, update, frames=n_frames, init_func=init, blit=True
    )

    if filepath is not None:
        animation.save(filepath, fps=30, dpi=200)

    return animation
