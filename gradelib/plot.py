import numpy as np
import altair
import pandas as pd

from . import scales as _scales


def grade_distribution(
    gb,
):
    """Visualize the grade distribution with respect to a scale.

    This will plot a histogram of the grade distribution, with each individual
    grade marked as a dot. Furthermore, if a gradine scale is provided,
    the letter grade thresholds are marked on the histogram as vertical lines,
    and the frequency of each letter grade is shown.

    Parameters
    ----------
    scores : pd.Series
        A series of scores between 0 and 1, with one score per student.
    scale : OrderedDict
        An ordered dictionary specifying the cutoffs for each letter grade.
        Optional. If `None` is passed, :attr:`DEFAULT_SCALE` is used. If
        `False` is passed, no scale will be displayed. Default: `None`.
    x_min : float
        The smallest extent of the axis containing scores. Default: 0.6
    x_max : float
        The greatest extent of the axis containing scores. Default: 1.02
    bins
        What to pass as the `bins` argument to `np.hist`. Default: "auto"

    """
    source = gb.overall_score.to_frame()
    source["Letter"] = gb.letter_grades
    source["Rank"] = gb.rank
    source["Percentile"] = gb.percentile
    source = source.reset_index().rename(columns={"index": "Name", 0: "Score"})
    source["Name"] = source["Name"].apply(lambda s: s.name)
    source["y"] = -1
    source["Formatted Score"] = source["Score"].apply(lambda s: f"{100*s:0.2f}%")

    hist = (
        altair.Chart(source)
        .mark_bar(binSpacing=0)
        .encode(
            x=altair.X(
                "Score",
                bin=altair.Bin(maxbins=50),
                scale=altair.Scale(domain=[0.6, 1.05]),
                axis=altair.Axis(title=None, values=list(gb.scale.values()) + [1]),
            ),
            y=altair.Y("count()", axis=altair.Axis(title="Count")),
        )
    )

    scatter = (
        altair.Chart(source)
        .mark_circle(color="red", opacity=0.5)
        .encode(
            x="Score",
            y="y",
            tooltip=["Name", "Formatted Score", "Letter", "Rank", "Percentile"],
        )
    )

    cutoffs_source = (
        pd.Series(gb.scale)
        .to_frame()
        .reset_index()
        .rename(columns={0: "thresh", "index": "letter"})
    )
    cutoffs_source["y"] = -2
    cutoffs_source["x"] = cutoffs_source["thresh"] + 0.005

    cutoffs = (
        altair.Chart(cutoffs_source)
        .mark_rule(color="black", size=1, strokeDash=[4, 4])
        .encode(x="thresh")
    )

    letters = (
        altair.Chart(cutoffs_source)
        .mark_text()
        .encode(
            text="letter",
            x="x",
            y="y",
        )
    )

    return (
        (hist + scatter + cutoffs + letters)
        .properties(width=800, height=400)
        .interactive()
    )
