import pytest
from src.utils.json_parser import strict_json_array

def test_parse_raw_array():
    text = '[{"feature_index":0,"classification":"REQUIRED"}]'
    arr = strict_json_array(text)
    assert isinstance(arr, list)
    assert arr[0]["feature_index"] == 0
    assert arr[0]["classification"] == "REQUIRED"

def test_parse_fenced_json():
    text = """```json
    [
      {"feature_index":0,"classification":"NOT REQUIRED"}
    ]
    ```"""
    arr = strict_json_array(text)
    assert isinstance(arr, list)
    assert arr[0]["classification"] == "NOT REQUIRED"

def test_invalid_raises():
    with pytest.raises(Exception):
        strict_json_array("nonsense text without json")