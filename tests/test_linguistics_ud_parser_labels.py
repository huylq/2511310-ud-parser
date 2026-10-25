"""Tests for mapping VTB dependency labels to interface base labels."""

from pathlib import Path

import pytest

from vietnlp.interfaces._common import UD_DEPREL
from vietnlp.linguistics import ud_parser


def _documented_label_pairs():
    design = (
        Path(__file__).resolve().parents[1]
        / "student-projects/02-ud-parsing/DESIGN.md"
    )
    _, heading, section = design.read_text(encoding="utf-8").partition(
        "## 14. Complete VTB label mapping"
    )
    assert heading, "Missing VTB label mapping section"
    pairs = []
    for line in section.splitlines():
        if line.startswith("| `"):
            fields = line.split("|")
            pairs.append((fields[1].strip().strip("`"), fields[2].strip().strip("`")))
    return pairs


VTB_LABEL_PAIRS = _documented_label_pairs()


def test_vtb_label_mapping_matches_documented_inventory():
    """Keep the code mapping consistent with the complete design table."""
    assert len(VTB_LABEL_PAIRS) == 84
    expected = dict(VTB_LABEL_PAIRS)
    assert len(expected) == 84
    assert len(set(expected.values())) == 34
    assert ud_parser.VTB_LABEL_MAPPING == expected


@pytest.mark.parametrize("label, expected", VTB_LABEL_PAIRS)
def test_map_deprel_vtb_label_to_base(label, expected):
    """Map every documented VTB label to its expected interface label."""
    result = ud_parser.map_deprel(label)
    assert result == expected
    assert result in UD_DEPREL


@pytest.mark.parametrize("label", sorted(UD_DEPREL))
def test_map_deprel_preserves_valid_base_labels(label):
    """Accept valid base labels even when absent from the VTB inventory."""
    assert ud_parser.map_deprel(label) == label


@pytest.mark.parametrize("label", ["", "_", "not_a_ud_relation"])
def test_map_deprel_rejects_unknown_labels(label):
    """Reject invalid labels instead of silently replacing them with dep."""
    with pytest.raises(ValueError):
        ud_parser.map_deprel(label)
