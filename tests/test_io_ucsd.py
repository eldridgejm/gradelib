import pathlib

import gradelib.io.ucsd

EXAMPLES_DIRECTORY = pathlib.Path(__file__).parent / "examples"

# read_egrades_roster
# =============================================================================


def test_read_egrades_roster():
    # when
    roster = gradelib.io.ucsd.read_egrades_roster(EXAMPLES_DIRECTORY / "egrades.csv")

    # then
    list(roster.index) == ["A12345678", "A10000000", "A16000000"]
