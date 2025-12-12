import html

from IPython.display import HTML as _HTML
from IPython.display import display as _display

from . import plot as _plot
from . import statistics as _statistics
from .core import Gradebook


def _item(desc, msg) -> str:
    """Returns HTML for an item with a description and a message."""
    return f"<p><b>{desc}:</b> {msg}"


def _display_html(html: str):
    """Display HTML in a Jupyter notebook."""
    _display(_HTML(html))


def _class_overview(gradebook: Gradebook):
    _display_html("<h1>Class Overview</h1>")
    _display_html(_item("Number of students", len(gradebook.students)))
    _display_html(
        _item("Average GPA", _statistics.average_gpa(gradebook.letter_grades))
    )

    _display_html("<h2>Letter Grade Distribution</h2>")
    _display_html(
        _statistics.letter_grade_distribution(gradebook.letter_grades)
        .to_frame()
        .T.to_html()
    )
    _plot.grade_distribution(gradebook)

    _display_html("<h2>Lates</h2>")
    _display_html(_statistics.lates(gradebook).to_html())

    _display_html("<h2>Individual Outcomes</h2>")
    _display_html(_statistics.outcomes(gradebook).to_html())


def _student_overview(gradebook: Gradebook, student_name: str):
    student = gradebook.students.find(student_name)
    student_name = html.escape(repr(student))

    _display_html(f"<h1>Student Overview: {student_name}</h1>")

    _display_html(_statistics.outcomes(gradebook).loc[student].to_frame().T.to_html())

    _display_html("<h2>Notes</h2>")
    notes = gradebook.notes[student]
    for channel in notes:
        _display_html(f"<h3>{channel.title()}</h3>")
        _display_html("<ul>")
        for note in notes[channel]:
            _display_html(f"<li>{html.escape(note)}</li>")
        _display_html("</ul>")


def overview(gradebook: Gradebook, student: str | None = None):
    """Display a nicely-formatted overview of a gradebook.

    Only availably inside of a jupyter notebook. Can be accessed from the
    top-level, too, as ``gradelib.overview()``.

    """
    if student is not None:
        _student_overview(gradebook, student)
    else:
        _class_overview(gradebook)
