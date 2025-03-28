import pathlib as _pathlib
import re as _re
import textwrap as _textwrap
from typing import Optional

from .core import Gradebook, Student
from . import statistics as _statistics


def _tex_escape(text):
    # from: https://stackoverflow.com/questions/16259923/how-can-i-escape-latex-special-characters-inside-django-templates
    conv = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\^{}",
        "\\": r"\textbackslash{}",
        "<": r"\textless{}",
        ">": r"\textgreater{}",
    }
    regex = _re.compile(
        "|".join(
            _re.escape(str(key))
            for key in sorted(conv.keys(), key=lambda item: -len(item))
        )
    )
    return regex.sub(lambda match: conv[match.group()], text)


def _default_percentile_display(pct):
    if pct >= 0.99:
        return "Top 1% of the class!"
    elif pct >= 0.95:
        return "Top 5% of the class!"
    elif pct >= 0.9:
        return "Top 10% of the class!"
    elif pct >= 0.75:
        return "Top 25% of the class."
    elif pct >= 0.5:
        return "Top half of the class."
    else:
        return None


def _null_percentile_display(pct):
    return None


def _student_latex_report(
    gradebook: Gradebook, student, show_percentile=_default_percentile_display
) -> str:
    if show_percentile is None:
        show_percentile = _null_percentile_display

    parts = []

    def _append(s):
        parts.append(_textwrap.dedent(s))

    _append(
        r"""
        \begin{center}
            \textsc{Overall Grade Report}
        \end{center}
        \vspace{4em}
    """
    )

    if student is None:
        student = Student("", "")

    if student.name is not None:
        _append(
            rf"""
            \textbf{{Name}}: {student.name}\\[2em]
        """
        )

    _append(
        rf"""
        \textbf{{PID}}: {student.pid}
        \vspace{{4em}}
    """
    )

    # student was None at start of function
    if student.pid == "":
        return "\n".join(parts)

    _append(r"\section*{Grades}")

    _append(
        r"""
        \begin{itemize}
    """
    )

    group_scores = gradebook.grading_group_scores.loc[student]
    for group_name in group_scores.index:
        score = group_scores[group_name]
        _append(
            rf"""
                \item \textbf{{{group_name.title()}}}: {score * 100:0.1f}\%
        """
        )

    _append(
        rf"""
        \end{{itemize}}

        \begin{{itemize}}
            \item \textbf{{Overall Score}}: {gradebook.overall_score.loc[student] * 100:0.1f}\%
            \item \textbf{{Letter Grade}}: {gradebook.letter_grades.loc[student]}
    """
    )

    percentile = _statistics.percentile(gradebook.overall_score).loc[student]
    percentile_message = show_percentile(percentile)

    if percentile_message is not None:
        _append(
            rf"""
            \item {_tex_escape(percentile_message)}
        """
        )

    _append(
        r"""
        \end{itemize}

        \section*{Notes}
    """
    )

    notes = gradebook.notes[student]
    for channel in notes:
        _append(
            rf"""
            \subsection*{{{channel.title()}}}

            \begin{{itemize}}
        """
        )
        for note in notes[channel]:
            _append(
                rf"""
                \item {_tex_escape(note)}
            """
            )

        _append(
            r"""
            \end{itemize}
        """
        )

    return "\n".join(parts)


def generate_latex(
    gradebook: Gradebook,
    output_directory: _pathlib.Path,
    show_percentile=_default_percentile_display,
    one_file=False,
):
    """Generate a LaTeX grade report for each student.

    Creates one file, `main.tex`, containing all of the reports.

    Parameters
    ----------
    gradebook : Gradebook
        The gradebook that will be used.
    output_directory : Union[pathlib.Path, str]
        The directory where the reports will be placed. Will be created if it
        does not already exist.
    show_percentile : Optional[Callable[[float], Optional[str]]]
        A function that takes in a percentile and returns a string that will be
        displayed to the student. If the output of the function is `None`, no
        message is displayed. If this is `None`, no messages are displayed to
        any students.
    one_file : bool
        If True, all student reports will be placed in a single file, `main.tex`.
        Otherwise, each student will have their own file (<pid>.tex). In either case,
        a `_template.tex` file will be created that can be used as a template for
        the gradebook application.

    """

    output_directory = _pathlib.Path(output_directory)
    output_directory.mkdir(exist_ok=True)

    head = _textwrap.dedent(
        r"""
            \documentclass{article}
            \usepackage[margin=1in]{geometry}
            \pagestyle{empty}
            \setlength{\parindent}{0em}
            \begin{document}
        """
    )

    tail = _textwrap.dedent(
        r"""
            \end{document}
        """
    )

    def make_student_report_file(student: Optional[Student]):
        """Create a LaTeX file for a student."""
        body = _student_latex_report(
            gradebook, student, show_percentile=show_percentile
        )
        document = head + body + tail

        if student is not None:
            filename = f"{student.pid}.tex"
        else:
            filename = "_template.tex"

        with (output_directory / filename).open("w") as fileobj:
            fileobj.write(document)

    def make_main_file():
        body = "\\newpage".join(
            _student_latex_report(gradebook, student, show_percentile=show_percentile)
            for student in gradebook.students
        )
        document = head + body + tail

        with output_directory.joinpath("main.tex").open("w") as fileobj:
            fileobj.write(document)

    if one_file:
        make_main_file()
    else:
        for student in gradebook.students:
            make_student_report_file(student)

    # saves a template file
    make_student_report_file(None)
