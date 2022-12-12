import html

from .core import Gradebook
from . import plot, summarize

from IPython.display import display, HTML


def _item(desc, msg):
    return f"<p><b>{desc}:</b> {msg}"

def _display_html(html):
    display(HTML(html))

def _class_overview(gradebook):

    _display_html('<h1>Class Overview</h1>')
    _display_html(_item('Number of students', len(gradebook.students)))
    _display_html(_item('Average GPA', summarize.average_gpa(gradebook.letter_grades)))

    _display_html('<h2>Letter Grade Distribution</h2>')
    _display_html(summarize.letter_grade_distribution(gradebook.letter_grades).to_frame().T.to_html())
    plot.grade_distribution(gradebook)

    _display_html('<h2>Lates</h2>')
    _display_html(summarize.lates(gradebook).to_html())

    _display_html('<h2>Individual Outcomes</h2>')
    _display_html(summarize.outcomes(gradebook).to_html())


def _student_overview(gradebook, student):
    student = gradebook.students.find(student)
    student_name = html.escape(repr(student))

    _display_html(f'<h1>Student Overview: {student_name}</h1>')

    _display_html(summarize.outcomes(gradebook).loc[student].to_frame().T.to_html())

    _display_html('<h2>Notes</h2>')
    notes = gradebook.notes[student]
    for channel in notes:
        _display_html(f'<h3>{channel.title()}</h3>')
        _display_html('<ul>')
        for note in notes[channel]:
            _display_html(f'<li>{html.escape(note)}</li>')
        _display_html('</ul>')





def overview(gradebook: Gradebook, student=None):
    """Display a nicely-formatted overview of a gradebook.

    Only availably inside of a jupyter notebook. Can be accessed from the
    top-level, too, as ``gradelib.overview()``.

    """
    if student is not None:
        _student_overview(gradebook, student)
    else:
        _class_overview(gradebook)






# summaries ------------------------------------------------------------------------


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
