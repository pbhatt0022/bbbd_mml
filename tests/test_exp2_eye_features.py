import gzip
import io
import json
from zipfile import ZipFile

import pytest

from bbbd.exp2_eye_features import read_eye


def test_eye_reader_checks_author_condition():
    name = "gaze.tsv.gz"
    metadata = {"Columns": ["x", "y"], "SamplingFrequency": 128, "StartTime": 0,
                "x": {"Units": "screen pixels"}, "y": {"Units": "screen pixels"}}
    for condition in ("Attentive", "Distracted"):
        with ZipFile(io.BytesIO(), "w") as archive:
            archive.writestr(name, gzip.compress(b"1\t2\n"))
            archive.writestr("gaze.json", json.dumps(
                dict(metadata, TaskName=f"Stim 01, {condition} Condition")
            ))
            if condition == "Attentive":
                assert read_eye(archive, name, ["x", "y"]).iloc[0].tolist() == [1, 2]
            else:
                with pytest.raises(ValueError, match="metadata"):
                    read_eye(archive, name, ["x", "y"])
