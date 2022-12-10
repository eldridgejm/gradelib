import numpy as np

from ..core import Percentage


def _fmt_as_pct(f):
    return f"{f * 100:0.2f}%"



class Redeem:
    def __init__(
        self, selector, remove_parts=False, deduction=None, suffix=" with redemption"
    ):
        self.selector = selector
        self.remove_parts = remove_parts
        self.deduction = deduction
        self.suffix = suffix

    def __call__(self, gradebook):
        if isinstance(self.selector, dict):
            assignment_pairs = self.selector
        else:
            assignment_pairs = {}
            for prefix in self.selector:
                pair = [a for a in gradebook.assignments if a.startswith(prefix)]
                if len(pair) != 2:
                    raise ValueError(
                        f'Prefix "{prefix}" does not match a pair of assignments.'
                    )
                assignment_pairs[prefix + self.suffix] = pair

        for new_name, assignment_pair in assignment_pairs.items():
            gradebook = self._redeem(gradebook, new_name, assignment_pair)

        if self.remove_parts:
            gradebook = self._remove_parts(gradebook)

        return gradebook

    def _redeem(self, gradebook, new_name, assignment_pair):
        first, second = assignment_pair

        if gradebook.dropped[[first, second]].values.any():
            raise ValueError("Cannot apply redemption to dropped assignments.")

        points_possible = gradebook.points_possible[[first, second]].max()

        first_scale, second_scale = (
            points_possible / gradebook.points_possible[[first, second]]
        )

        first_points = gradebook.points_earned[first] * first_scale
        second_points = gradebook.points_earned[second] * second_scale

        first_points = first_points.fillna(0)
        second_points = second_points.fillna(0)

        if self.deduction is not None:
            if isinstance(self.deduction, Percentage):
                d = points_possible * self.deduction.amount
            else:
                d = self.deduction.amount

            second_points = second_points - d

        points_earned = np.maximum(first_points, second_points)

        # used for messaging
        first_raw_score = gradebook.points_earned[first] / gradebook.points_possible[first]
        second_raw_score = gradebook.points_earned[second] / gradebook.points_possible[second]

        def _fmt_score(score):
            if np.isnan(score):
                return 'n/a'
            else:
                return _fmt_as_pct(score)

        for pid in points_earned.index:
            first_score_string = _fmt_score(first_raw_score.loc[pid])
            second_score_string = _fmt_score(second_raw_score.loc[pid])
            pieces = [
                f"{first.title()} score: {first_score_string}.",
                f"{second.title()} score: {second_score_string}."
            ]
            if first_points.loc[pid] >= second_points.loc[pid]:
                pieces.append(f"{first.title()} score used.")
            else:
                pieces.append(f"{second.title()} score used.")
            gradebook.add_note(pid, "redemption", " ".join(pieces))

        gradebook.add_assignment(new_name, points_earned, points_possible)
        return gradebook

    def _remove_parts(self, gradebook):
        for assignment_pair in self.selector.values():
            gradebook.remove_assignments(assignment_pair)
        return gradebook
