import numpy as np
import altair
import pandas as pd

from . import scales as _scales

def plot_grade_distribution(
    scores,
    scale=None,
    x_min=0.6,
    x_max=1.02,
    bins="auto",
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
    if scale is None:
        scale = DEFAULT_SCALE

    # discard scores below the minimum
    scores = scores[scores >= x_min]

    scores = scores.sort_values()
    h = plt.hist(scores, bins=bins, density=True, color="blue", alpha=0.5)
    plt.scatter(
        scores, np.zeros_like(scores) - 0.1, marker="o", color="red", s=20, zorder=10
    )

    if scale:
        letters = map_scores_to_letter_grades(scores, scale)
        counts = letter_grade_distribution(letters)
        for letter, threshold in scale.items():
            if threshold > x_min:
                plt.axvline(threshold, color="black", linestyle=":")
                plt.text(threshold + 0.002, -0.6, f"{letter} ({counts[letter]})")

    plt.xlim([x_min, x_max])
    plt.ylim([-1, h[0].max() * 1.1])

    ax = plt.gca()
    ax.set_yticks([])




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

# summaries ------------------------------------------------------------------------


def _assignment_plot(self, pid):
    data = self.score.loc[pid].to_frame(name="Score")
    data["Notes"] = self.dropped.loc[pid].apply(lambda d: "dropped" if d else "")

    data = (
        data.sort_index()
        .reset_index()
        .rename(columns={"index": "Assignment"})
        .reset_index()
        .fillna(0)
    )

    data["Formatted Score"] = data["Score"].apply(lambda s: f"{s * 100:0.2f}%")

    bars = (
        altair.Chart(data)
        .mark_bar()
        .encode(x="Score:Q", y="Assignment:N", tooltip="Formatted Score")
    )

    text = (
        altair.Chart(data)
        .mark_text(
            align="left",
            baseline="middle",
            color="black",
            fontWeight="bold",
            dx=3,  # Nudges text to right so it doesn't appear on top of the bar
        )
        .encode(x="Score:Q", y="Assignment:N", text="Notes:N")
    )

    return bars + text


def _student_summary(self, student):
    from IPython.display import display, HTML

    lines = []

    def par(desc, msg):
        lines.append(f"<p><b>{desc}:</b> {msg}</p>")

    def li(desc, msg):
        lines.append(f"<li><b>{desc}:</b> {msg}</li>")

    def _fmt_as_pct(f):
        return f"{f * 100:0.2f}%"

    name = student.name
    pid = student.pid

    lines.append(f"<h1>Student Summary: {name} ({pid})</h1>")

    par("Overall score", f"{_fmt_as_pct(self.overall_score.loc[pid])}")
    par("Letter grade", self.letter_grades.loc[pid])
    par("Rank", f"{self.rank.loc[pid]} out of {len(self.rank)}")
    par("Percentile", f"{self.percentile.loc[pid]:0.2f}")

    lines.append("<h2>Group Scores</h2>")
    lines.append("<ul>")
    for group in self.assignment_groups:
        score = self.assignment_group_scores.loc[pid, group.name]
        li(group.name, _fmt_as_pct(score))
    lines.append("</ul>")

    notes = self.notes.get(pid, None)
    if notes is not None:
        lines.append("<h2>Notes</h2>")
        for channel in notes:
            lines.append(f"<h3>{channel.capitalize()}</h3>")
            lines.append("<ul>")
            for note in notes[channel]:
                lines.append(f"<li>{note}</li>")
            lines.append("</ul>")

    display(HTML("\n".join(lines)))

    display(self._assignment_plot(pid))


def _class_summary(self):
    from IPython.display import display, HTML

    lines = []

    def item(desc, msg):
        lines.append(f"<p><b>{desc}:</b> {msg}")

    lines.append("<h1>Class Summary</h1>")

    item("Number of students", len(self.students))

    lines.append("<h2>Letter Grades</h2>")

    lines.append(self.letter_grade_distribution.to_frame().T.to_html())

    agpa = average_gpa(self.letter_grades)
    lines.append(f"<p><b>Class GPA:</b> {agpa:0.2f}</p>")
    lines.append("<h2>Distribution</h2>")

    display(HTML("\n".join(lines)))

    display(_plot.grade_distribution(self))


def summary(self, student=None):
    if student is not None:
        return self._student_summary(self.find_student(student))
    else:
        return self._class_summary()


