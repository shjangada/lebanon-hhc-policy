import pathlib
import pandas as pd
import pytest

from beqaa import io

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", sorted(io.DATASETS))
def test_mock_loads_and_flagged(name):
    df, is_mock = io.load_dataset(name)
    assert is_mock and len(df) > 0 and df["is_mock"].all()


def test_real_overrides_mock(tmp_path):
    pd.DataFrame({"district": ["X"], "jiaf_severity": [1]}).to_csv(tmp_path / "official_severity.csv", index=False)
    df, is_mock = io.load_dataset("official_severity", raw_dir=tmp_path)
    assert not is_mock and list(df.district) == ["X"]


def test_status_all_mock_without_raw(tmp_path):
    assert io.overall_mode(tmp_path) == "MOCK"
    assert io.data_status(tmp_path).status.str.contains("🔴").all()


def test_unknown_dataset():
    with pytest.raises(KeyError):
        io.load_dataset("nope")
