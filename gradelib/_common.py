from __future__ import annotations


def in_jupyter_notebook():
    try:
        shell = get_ipython().__class__.__name__  # pyright: ignore
        if shell == "ZMQInteractiveShell":
            return True  # Jupyter notebook or qtconsole
        elif shell == "TerminalInteractiveShell":
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False


def resolve_assignment_selector(within, assignments):
    if within is None:
        within = assignments

    if callable(within):
        within = within(assignments)

    if not within:
        raise ValueError("Cannot use an empty list of assignments.")

    return list(within)
