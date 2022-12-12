***********
Quick Start
***********

The following example shows the complete workflow for calculating final grades
in a typical scenario. In this case, some grades were kept on Canvas, while
others were kept on Gradescope. The grading policy allowed for 4 late
assignments between homeworks and labs, as well as one dropped homework and one
dropped lab. The final grading scale is determined by a simple clustering
algorithm which finds "robust" thresholds for every letter grade.

.. code:: python

    import gradelib

    gb = gradelib.combine_gradebooks([
        gradelib.io.gradescope.read('./gradescope.csv'),
        gradelib.io.canvas.read('./canvas.csv')
    ])

    # define assignment groups
    HOMEWORKS = gradelib.LazyAssignments().starting_with('home')
    LABS = gradelib.LazyAssignments().starting_with('lab')

    # merge assignment versions
    gradelib.preprocessing.combine_assignment_versions(['midterm 01', 'midterm 02'])

    # unify assignments that have multiple parts, such as "homework 01" and
    # "homework 01 - programming problem"
    gradelib.preprocessing.combine_assignment_parts(
        lambda a: a.split('-')[0].strip(),
        within=HOMEWORKS
    )

    # handle exceptions
    gradelib.policies.make_exceptions({
        'me': [
            gradelib.policies.Drop("homework 01", reason="illness"),
            gradelib.policies.Replace("homework 02", with_=gradelib.Percentage(.75))
        ],
        'you': [
            gradelib.policies.ForgiveLate("homework 01", reason="illness"),
        ],
    })

    # apply grading policies
    gradelib.policies.penalize_lates(gb, forgive=4, within=HOMEWORKS+LABS)
    gradelib.policies.drop_lowest(gb, 1, within=HOMEWORKS)
    gradelib.policies.drop_lowest(gb, 1, within=LABS)
    gradelib.policies.redeem({
        'midterm 01 - with redemption': ['midterm 01', 'redemption midterm 01'],
        'midterm 02 - with redemption': ['midterm 02', 'redemption midterm 02']
    })

    gb.grading_groups = {
        'homeworks': (HOMEWORKS, .25),
        'labs': (LABS, .25),
        'project 01': .05,
        'project 02': .10,
        'midterm exam': .1,
        'final exam': .1
    }

    # find robust letter grade cutoffs by clustering grades
    gb.scale = gradelib.scales.find_robust_scale(gb.overall_scores)

    # visualize the grade distribution
    gradelib.plot.grade_distribution(gb)

    # view an interactive overview of the class's performance
    gradelib.overview(gb)

    # view a single student's performance and grading notes
    gradelib.overview(gb, student='me')

    # generate student reports, complete with auto-generated grading notes about which
    # assignments were dropped, penalized for being late, etc.
    gradelib.reports.generate_latex(gb)
