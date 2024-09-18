import json
from pathlib import Path

from py3dtiles.tileset.extension.batch_table_hierarchy_extension import (
    BatchTableHierarchy,
)


def test_bth_build_sample_with_indexes_and_compare_reference_file(
    batch_table_hierarchy_with_indexes: BatchTableHierarchy,
    batch_table_hierarchy_reference_file: Path,
) -> None:
    """
    Build the sample, load the version from the reference file and
    compare them (in memory as opposed to "diffing" files)
    """
    json_bth = batch_table_hierarchy_with_indexes.to_dict()

    with batch_table_hierarchy_reference_file.open() as reference_file:
        json_reference = json.loads(reference_file.read())

    json_reference.pop("_comment", None)  # Drop the "comment".

    assert json_bth == json_reference


def test_bth_build_sample_with_instances_and_compare_reference_file(
    batch_table_hierarchy_with_instances: BatchTableHierarchy,
    batch_table_hierarchy_reference_file: Path,
) -> None:
    """
    Build the sample, load the version from the reference file and
    compare them (in memory as opposed to "diffing" files)
    """
    json_bth = batch_table_hierarchy_with_instances.to_dict()

    with batch_table_hierarchy_reference_file.open() as reference_file:
        json_reference = json.loads(reference_file.read())

    json_reference.pop("_comment", None)  # Drop the "comment".

    assert json_bth == json_reference
