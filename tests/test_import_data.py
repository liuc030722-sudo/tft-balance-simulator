"""CSV import validation with synthetic test fixtures, not TFT game data."""

import csv
import json

import pytest

from tft_simulator.database.import_data import STAT_COLUMNS, load_dataset


@pytest.fixture
def csv_dataset(tmp_path):
    # 这些值仅用于单元测试，不是假定或编造的真实英雄属性。
    source = {
        "set_number": 10, "patch_directory": "test-patch",
        "source_url": "https://example.invalid/unit-test",
        "sha256": "a" * 64, "retrieved_at_utc": "2026-01-01T00:00:00+00:00",
    }
    provenance = {
        "set_number": "10", "patch": "test-patch",
        "source_url": source["source_url"], "source_sha256": source["sha256"],
    }
    champion = {
        **provenance, "champion_id": "TEST_ONLY", "name": "Synthetic fixture",
        "cost": "1", "traits_json": '["TestTrait"]', "role_raw": "",
        **{column: "1.0" for column in STAT_COLUMNS},
    }
    ability = {
        **provenance, "champion_id": "TEST_ONLY", "ability_name": "Test ability",
        "description_raw": "Synthetic fixture only", "variables_json": "[]",
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(source), encoding="utf-8")

    def write(champions=None, abilities=None):
        # 通过真实CSV文件测试解码和关联检查，不模拟数据库实现细节。
        champion_path = tmp_path / "champions.csv"
        ability_path = tmp_path / "abilities.csv"
        for path, template, rows in (
            (champion_path, champion, [champion] if champions is None else champions),
            (ability_path, ability, [ability] if abilities is None else abilities),
        ):
            with path.open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=list(template))
                writer.writeheader()
                writer.writerows(rows)
        return champion_path, ability_path, manifest_path

    return write, champion, ability


def test_csv_types_and_json_are_restored(csv_dataset):
    # 验证CSV文本能转换为数据库需要的数值、列表和带时区时间。
    write, _, _ = csv_dataset
    version, champions, abilities = load_dataset(*write())
    assert version["retrieved_at_utc"].utcoffset() is not None
    assert champions[0]["traits"] == ["TestTrait"]
    assert champions[0]["hp"] == 1.0
    assert champions[0]["role_raw"] is None
    assert abilities[0]["variables"] == []


def test_duplicate_champion_is_rejected(csv_dataset):
    # 重复ID不能被ON CONFLICT静默吞掉，应在入库之前报告输入问题。
    write, champion, _ = csv_dataset
    with pytest.raises(ValueError, match="duplicate"):
        load_dataset(*write(champions=[champion, champion]))


def test_mixed_source_is_rejected(csv_dataset):
    # 不允许将其他快照的数据标记为当前来源。
    write, _, ability = csv_dataset
    with pytest.raises(ValueError, match="provenance"):
        load_dataset(*write(abilities=[dict(ability, source_sha256="b" * 64)]))


def test_missing_ability_is_rejected(csv_dataset):
    # 当前导入任务要求每个选定英雄都具有对应的技能归档记录。
    write, _, _ = csv_dataset
    with pytest.raises(ValueError, match="matching"):
        load_dataset(*write(abilities=[]))


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_nonfinite_stats_are_rejected(csv_dataset, value):
    # PostgreSQL浮点字段可接受特殊值，但此项目的基础属性不接受它们。
    write, champion, _ = csv_dataset
    with pytest.raises(ValueError, match="Nonfinite"):
        load_dataset(*write(champions=[dict(champion, hp=value)]))
