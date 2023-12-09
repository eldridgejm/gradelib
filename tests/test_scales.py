import gradelib

import pandas as pd


def test_map_score_to_letter_grade_on_example():
    # given
    scores = pd.Series(data=[0.84, 0.95, 0.55])

    # when
    letters = gradelib.scales.map_scores_to_letter_grades(scores)

    # then
    letters.iloc[0] = "B"
    letters.iloc[1] = "A"
    letters.iloc[2] = "F"
