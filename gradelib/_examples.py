"""Examples that are used in the documentation."""

import gradelib

import numpy as np
import pandas as pd


def with_lates():
    students = ["Justin", "Barack"]
    assignments = ["Homework 01", "Homework 02", "Homework 03"]

    points_earned = pd.DataFrame(
        [[7, 5, 9], [10, 8, 7]],
        index=students,
        columns=assignments,
    )

    points_possible = pd.Series(
        [10, 10, 10],
        index=assignments,
    )

    lateness = pd.DataFrame(
        [pd.to_timedelta([5000, 5000, 5000], "s"), pd.to_timedelta([6000, 0, 0], "s")],
        columns=assignments,
        index=students,
    )

    return gradelib.Gradebook(
        points_earned=points_earned,
        points_possible=points_possible,
        lateness=lateness,
    )
