"""A simple tool to manage grading workflows."""

from .core import Gradebook


class Pipeline:
    """Manage the steps of a grading workflow.

    Grading is often done in Jupyter notebooks. While convenient, they are
    susceptible to subtle errors when cells are run out of order.

    To avoid this, it is recommended to define the steps of the grading workflow
    as functions in a pipeline. Instead of running each step individually, the
    entire pipeline is run at once to produce a single finalized gradebook,
    thus preventing subtle errors that can occur when cells are run out of
    order.

    Once the pipeline has been instantiated, steps can be be created by using
    the :meth:`step` method as a decorator. The first step should accept no
    arguments and should return a :class:`Gradebook`. Subsequent steps should
    take in a :class:`Gradebook` and modify it. This modified gradebook is
    passed to the next step, ad infinitum. Alternatively, if a step returns a
    :class:`Gradebook`, it is passed to the next step instead.

    Finally, to run the entire pipeline at once, use :meth:`grade`.

    Example
    -------

    .. code:: python

        pipeline = gradelib.Pipeline()

        homeworks = gradelib.LazyAssignments(lambda asmts: asmts.starting_with('home'))
        labs = gradelib.LazyAssignments(lambda asmts: asmts.starting_with('lab'))

        @pipeline.step(0)
        def load():
            return gradelib.io.gradescope.read('./path/to/grade.csv')

        @pipeline.step(1)
        def preprocess(gb):
            # merge homework parts
            preprocessing.combine_assignment_parts(
                    gb, lambda a: a.split('-')[0], within=homeworks
            )

            # merge versions
            preprocessing.combine_assignment_versions(
                    gb, lambda a: a.plit('-')[0], within=['midterm - a', 'midterm - b']
            )

            gb.grading_groups = {
                'homeworks': (homeworks, 0.5),
                'labs': (labs, 0.25),
                'midterm': 0.25
            }

        @pipeline.step(2)
        def apply_policies(gb):
            gradelib.policies.drop_lowest(gb, 1, within=homeworks)
            gradelib.policies.penalize_lates(gb, forgive=3, within=homeworks+labs)

        gb = pipeline.grade()
    """

    def __init__(self):
        self.steps = {}

    def step(self, number):
        """Decorator for defining a grading step."""

        def decorator(func):
            self.steps[number] = func
            return func

        return decorator

    def grade(self) -> Gradebook:
        """Run the grading workflow to produce a finalized gradebook."""
        steps = [self.steps[k] for k in sorted(self.steps)]
        gb = steps[0]()

        if not isinstance(gb, Gradebook):
            raise ValueError("First step should return a Gradebook.")

        for step in steps[1:]:
            res = step(gb)
            if res is not None:
                gb = res
        return gb
