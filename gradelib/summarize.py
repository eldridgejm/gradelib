
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

# properties: ranks and percentiles

@property
def rank(self) -> pd.Series:
    """A series containing the rank of each student according to overall score.

    A pandas Series with an entry for each student in the Gradebook. The
    index is the same as the series returned by the :attr:`students`
    attribute. Each entry is the rank in the class, taking drops into
    account, and calculated using the value of the :attr:`overall_score`
    attribute.

    This is a dynamically-computed property; it should not be modified.

    Raises
    ------
    ValueError
        If :attr:`assignment_groups` has not yet been set.

    """
    sorted_scores = self.overall_score.sort_values(ascending=False).to_frame()
    sorted_scores["rank"] = np.arange(1, len(sorted_scores) + 1)
    return sorted_scores["rank"]

@property
def percentile(self) -> pd.Series:
    """A series containing the percentile of each student according to overall score.

    A pandas Series with an entry for each student in the Gradebook. The
    index is the same as the series returned by the :attr:`students`
    attribute. Each entry is the percentile in the class, taking drops into
    account, and calculated using the value of the :attr:`overall_score`
    attribute.

    This is a dynamically-computed property; it should not be modified.

    Raises
    ------
    ValueError
        If :attr:`assignment_groups` has not yet been set.

    """
    s = 1 - ((self.rank - 1) / len(self.rank))
    s.name = "percentile"
    return s

