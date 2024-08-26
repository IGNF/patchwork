import sys

import pytest
from hydra import compose, initialize
import laspy
import numpy as np
import pandas as pd

sys.path.append('../patchwork')

from patchwork import get_complementary_points, get_field_from_header, get_selected_classes_points
from patchwork import get_type, append_points

RECIPIENT_TEST_PATH = "test/data/recipient_test.laz"
RECIPIENT_CLASS_LIST = [2, 3, 9, 17]
DONOR_TEST_PATH = "test/data/donor_test.las"


def test_get_field_from_header():
    with laspy.open(RECIPIENT_TEST_PATH) as recipient_file:
        recipient_fields_list = get_field_from_header(recipient_file)
        assert len(recipient_fields_list) == 18
        # check if all fields are lower case
        assert [field for field in recipient_fields_list if field != field.lower()] == []


def test_get_selected_classes_points():

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.RECIPIENT_FILE={RECIPIENT_TEST_PATH}",
                f"RECIPIENT_CLASS_LIST={RECIPIENT_CLASS_LIST}"
            ]
        )

    with laspy.open(config.filepath.RECIPIENT_FILE) as recipient_file:
        recipient_points = recipient_file.read().points

        df_recipient_points = get_selected_classes_points(config, recipient_points, config.RECIPIENT_CLASS_LIST, [])
        for classification in np.unique(df_recipient_points['classification']):
            assert classification in RECIPIENT_CLASS_LIST


def test_get_complementary_points():
    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.DONOR_FILE={DONOR_TEST_PATH}",
                f"filepath.RECIPIENT_FILE={RECIPIENT_TEST_PATH}",
            ]
        )

        complementary_points = get_complementary_points(config)
        assert len(complementary_points) == 320


def test_get_type():
    assert get_type(8) == np.int8
    with pytest.raises(Exception):
        get_type(7)


def get_point_count(file_path):
    with laspy.open(file_path) as file:
        return file.header.point_count


def test_append_points(tmp_path_factory):
    tmp_file_path = tmp_path_factory.mktemp("data") / "result.laz"

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.RECIPIENT_FILE={RECIPIENT_TEST_PATH}",
                f"filepath.OUTPUT_FILE={tmp_file_path}"
            ]
        )

        point_count = get_point_count(config.filepath.RECIPIENT_FILE)
        extra_points = pd.DataFrame(data={'x': [1, ], 'y': [2, ], 'z': [3, ], 'classification': [4, ], })
        append_points(config, extra_points)
        assert get_point_count(config.filepath.OUTPUT_FILE) == point_count + 1
