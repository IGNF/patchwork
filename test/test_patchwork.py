import sys

import pytest
from hydra import compose, initialize
import laspy
import numpy as np
import pandas as pd

sys.path.append('../patchwork')

from patchwork import get_complementary_points, get_field_from_header, get_selected_classes_points
from patchwork import get_type, append_points, CLASSIFICATION_STR

RECIPIENT_TEST_PATH = "test/data/recipient_test.laz"
RECIPIENT_CLASS_LIST = [2, 3, 9, 17]
DONOR_TEST_PATH = "test/data/donor_test.las"

RECIPIENT_MORE_FIELDS_TEST_PATH = "test/data/recipient_more_fields_test.laz"
DONOR_MORE_FIELDS_TEST_PATH = "test/data/donor_more_fields_test.las"

RECIPIENT_SLIDED_TEST_PATH = "test/data/recipient_slided_test.laz"

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
        for classification in np.unique(df_recipient_points[CLASSIFICATION_STR]):
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

def test_get_complementary_points_2():
    """test selected_classes_points with more fields in files, different from each other's"""
    extra_fields_for_recipient = ["f1","f2"]
    las = laspy.read(RECIPIENT_TEST_PATH)
    for field in extra_fields_for_recipient:
        las.add_extra_dim(laspy.ExtraBytesParams(name=field, type=np.uint64))
    las.write(RECIPIENT_MORE_FIELDS_TEST_PATH)

    extra_fields_for_donor = ["f3","f4"]
    las = laspy.read(DONOR_TEST_PATH)
    for field in extra_fields_for_donor:
        las.add_extra_dim(laspy.ExtraBytesParams(name=field, type=np.uint64))
    las.write(DONOR_MORE_FIELDS_TEST_PATH)

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.DONOR_FILE={DONOR_MORE_FIELDS_TEST_PATH}",
                f"filepath.RECIPIENT_FILE={RECIPIENT_MORE_FIELDS_TEST_PATH}",
            ]
        )

        complementary_points = get_complementary_points(config)
        assert len(complementary_points) == 320
        columns = complementary_points.columns
        for field in extra_fields_for_recipient:  # no extra field from the recipient should exist
            assert field not in columns
        for field in extra_fields_for_donor:  # every extra field from the donor should exist...
            assert field in columns
            assert complementary_points[field].all() == 0 # ...but should be at 0


def test_get_complementary_points_3():
    """test selected_classes_points with 2 files from different areas"""
    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.DONOR_FILE={DONOR_TEST_PATH}",
                f"filepath.RECIPIENT_FILE={RECIPIENT_SLIDED_TEST_PATH}",
            ]
        )

        las = laspy.read(RECIPIENT_TEST_PATH)
        las.points['x'] = las.points['x'] + config.TILE_SIZE
        las.write(RECIPIENT_SLIDED_TEST_PATH)

        with pytest.raises(Exception):
            get_complementary_points(config)


def test_get_type():
    assert get_type(8) == np.int8
    assert get_type(16) == np.int16
    assert get_type(32) == np.int32
    assert get_type(64) == np.int64
    with pytest.raises(Exception):
        get_type(7)


def get_point_count(file_path):
    with laspy.open(file_path) as file:
        return file.header.point_count


def test_append_points(tmp_path_factory):
    tmp_file_path = tmp_path_factory.mktemp("data") / "result.laz"
    point_1 = {'x': 1, 'y': 2, 'z': 3, CLASSIFICATION_STR: 4}
    point_2 = {'x': 5, 'y': 6, 'z': 7, CLASSIFICATION_STR: 8}

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.RECIPIENT_FILE={RECIPIENT_TEST_PATH}",
                f"filepath.OUTPUT_FILE={tmp_file_path}"
            ]
        )

        # add 2 points
        extra_points = pd.DataFrame(data=[point_1, point_2])
        append_points(config, extra_points)

        # assert a point has been added
        point_count = get_point_count(config.filepath.RECIPIENT_FILE)
        assert get_point_count(config.filepath.OUTPUT_FILE) == point_count + 2

        # assert fields are the same
        fields_recipient = get_field_from_header(laspy.read(config.filepath.RECIPIENT_FILE))
        fields_output = get_field_from_header(laspy.read(config.filepath.OUTPUT_FILE))
        assert set(fields_recipient) == set(fields_output)

        # assert all points are here
        las_recipient = laspy.read(config.filepath.RECIPIENT_FILE)
        las_output = laspy.read(config.filepath.OUTPUT_FILE)
        for point in las_recipient.points[:10]:  # only 10 points, otherwise it takes too long
            assert point in las_output.points

        # add 1 point
        extra_points = pd.DataFrame(data=[point_1, ])
        append_points(config, extra_points)

        # assert a point has been added
        point_count = get_point_count(config.filepath.RECIPIENT_FILE)
        assert get_point_count(config.filepath.OUTPUT_FILE) == point_count + 1

        # # add 0 point
        extra_points = pd.DataFrame(data={'x': [], 'y': [], 'z': [], CLASSIFICATION_STR: []})
        append_points(config, extra_points)

        # assert a point has been added
        point_count = get_point_count(config.filepath.RECIPIENT_FILE)
        assert get_point_count(config.filepath.OUTPUT_FILE) == point_count