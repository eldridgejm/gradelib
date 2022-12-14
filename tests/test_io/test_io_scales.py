from gradelib.scales import DEFAULT_SCALE
import gradelib


def test_roundtrip(tmp_path):
    # given
    scale = DEFAULT_SCALE

    # when
    gradelib.io.scales.write(tmp_path / "scale.csv", scale)
    roundtripped_scale = gradelib.io.scales.read(tmp_path / "scale.csv")

    # then
    assert roundtripped_scale == scale
