import os

import laspy
import numpy as np
import pandas as pd
import pytest
from hydra import compose, initialize
from pandas import DataFrame

import patchwork.constants as c
from patchwork.patchwork import (
    append_points,
    get_complementary_points,
    get_donor_from_csv,
    get_donor_path,
    get_field_from_header,
    get_selected_classes_points,
    get_type,
)
from patchwork.tools import get_tile_origin_from_pointcloud

RECIPIENT_TEST_DIR = "test/data/"
RECIPIENT_TEST_NAME = "recipient_test.laz"

DONOR_CLASS_LIST = [2, 9]
RECIPIENT_CLASS_LIST = [2, 3, 9, 17]
VIRTUAL_CLASS_TRANSLATION = {2: 69, 9: 70}
POINT_1 = {"x": 1, "y": 2, "z": 3, c.CLASSIFICATION_STR: 4}
POINT_2 = {"x": 5, "y": 6, "z": 7, c.CLASSIFICATION_STR: 8}
NEW_COLUMN = "virtual_column"
NEW_COLUMN_SIZE = 8
VALUE_ADDED_POINTS = 1

DONOR_TEST_DIR = "test/data/"
DONOR_TEST_NAME = "donor_test.las"

RECIPIENT_MORE_FIELDS_TEST_DIR = "test/data"
RECIPIENT_MORE_FIELDS_TEST_NAME = "recipient_more_fields_test.laz"

DONOR_MORE_FIELDS_TEST_DIR = "test/data"
DONOR_MORE_FIELDS_TEST_NAME = "donor_more_fields_test.las"

RECIPIENT_SLIDED_TEST_DIR = "test/data"
RECIPIENT_SLIDED_TEST_NAME = "recipient_slided_test.laz"


COORDINATES = "1234_6789"


def test_get_field_from_header():
    with laspy.open(os.path.join(RECIPIENT_TEST_DIR, RECIPIENT_TEST_NAME)) as recipient_file:
        recipient_fields_list = get_field_from_header(recipient_file)
        assert len(recipient_fields_list) == 18
        # check if all fields are lower case
        assert [field for field in recipient_fields_list if field != field.lower()] == []


def test_get_selected_classes_points():

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.RECIPIENT_DIRECTORY={RECIPIENT_TEST_DIR}",
                f"filepath.RECIPIENT_NAME={RECIPIENT_TEST_NAME}",
                f"RECIPIENT_CLASS_LIST={RECIPIENT_CLASS_LIST}",
            ],
        )

        with laspy.open(
            os.path.join(config.filepath.RECIPIENT_DIRECTORY, config.filepath.RECIPIENT_NAME)
        ) as recipient_file:
            recipient_points = recipient_file.read().points

            tile_origin_recipient = get_tile_origin_from_pointcloud(config, recipient_points)

            df_recipient_points = get_selected_classes_points(
                config, tile_origin_recipient, recipient_points, config.RECIPIENT_CLASS_LIST, []
            )
            for classification in np.unique(df_recipient_points[c.CLASSIFICATION_STR]):
                assert classification in RECIPIENT_CLASS_LIST


def test_get_complementary_points():
    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.DONOR_DIRECTORY={DONOR_TEST_DIR}",
                f"filepath.DONOR_NAME={DONOR_TEST_NAME}",
                f"filepath.RECIPIENT_DIRECTORY={RECIPIENT_TEST_DIR}",
                f"filepath.RECIPIENT_NAME={RECIPIENT_TEST_NAME}",
                f"DONOR_CLASS_LIST={DONOR_CLASS_LIST}",
                f"RECIPIENT_CLASS_LIST={RECIPIENT_CLASS_LIST}",
                f"+VIRTUAL_CLASS_TRANSLATION={VIRTUAL_CLASS_TRANSLATION}",
            ],
        )

        complementary_points = get_complementary_points(config)
        assert len(complementary_points) == 320


def test_get_complementary_points_2():
    """test selected_classes_points with more fields in files, different from each other's"""
    extra_fields_for_recipient = ["f1", "f2"]
    las = laspy.read(os.path.join(RECIPIENT_TEST_DIR, RECIPIENT_TEST_NAME))
    for field in extra_fields_for_recipient:
        las.add_extra_dim(laspy.ExtraBytesParams(name=field, type=np.uint64))
    las.write(os.path.join(RECIPIENT_MORE_FIELDS_TEST_DIR, RECIPIENT_MORE_FIELDS_TEST_NAME))

    extra_fields_for_donor = ["f3", "f4"]
    las = laspy.read(os.path.join(DONOR_TEST_DIR, DONOR_TEST_NAME))
    for field in extra_fields_for_donor:
        las.add_extra_dim(laspy.ExtraBytesParams(name=field, type=np.uint64))
    las.write(os.path.join(DONOR_MORE_FIELDS_TEST_DIR, DONOR_MORE_FIELDS_TEST_NAME))

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.RECIPIENT_DIRECTORY={RECIPIENT_MORE_FIELDS_TEST_DIR}",
                f"filepath.RECIPIENT_NAME={RECIPIENT_MORE_FIELDS_TEST_NAME}",
                f"filepath.DONOR_DIRECTORY={DONOR_MORE_FIELDS_TEST_DIR}",
                f"filepath.DONOR_NAME={DONOR_MORE_FIELDS_TEST_NAME}",
                f"DONOR_CLASS_LIST={DONOR_CLASS_LIST}",
                f"RECIPIENT_CLASS_LIST={RECIPIENT_CLASS_LIST}",
                f"+VIRTUAL_CLASS_TRANSLATION={VIRTUAL_CLASS_TRANSLATION}",
            ],
        )

        complementary_points = get_complementary_points(config)
        assert len(complementary_points) == 320
        columns = complementary_points.columns
        for field in extra_fields_for_recipient:  # no extra field from the recipient should exist
            assert field not in columns
        for field in extra_fields_for_donor:  # every extra field from the donor should exist...
            assert field in columns
            assert complementary_points[field].all() == 0  # ...but should be at 0


def test_get_complementary_points_3():
    """test selected_classes_points with 2 files from different areas"""
    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.DONOR_DIRECTORY={DONOR_TEST_DIR}",
                f"filepath.DONOR_NAME={DONOR_TEST_NAME}",
                f"filepath.RECIPIENT_DIRECTORY={RECIPIENT_SLIDED_TEST_DIR}",
                f"filepath.RECIPIENT_NAME={RECIPIENT_SLIDED_TEST_NAME}",
            ],
        )

        las = laspy.read(os.path.join(RECIPIENT_TEST_DIR, RECIPIENT_TEST_NAME))
        las.points["x"] = las.points["x"] + config.TILE_SIZE
        las.write(os.path.join(RECIPIENT_SLIDED_TEST_DIR, RECIPIENT_SLIDED_TEST_NAME))

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
    tmp_file_dir = tmp_path_factory.mktemp("data")
    tmp_file_name = "result.laz"

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.RECIPIENT_DIRECTORY={RECIPIENT_TEST_DIR}",
                f"filepath.RECIPIENT_NAME={RECIPIENT_TEST_NAME}",
                f"filepath.OUTPUT_DIR={tmp_file_dir}",
                f"filepath.OUTPUT_NAME={tmp_file_name}",
            ],
        )

        recipient_file_path = os.path.join(config.filepath.RECIPIENT_DIRECTORY, config.filepath.RECIPIENT_NAME)
        output_file = os.path.join(config.filepath.OUTPUT_DIR, config.filepath.OUTPUT_NAME)

        # add 2 points
        extra_points = pd.DataFrame(data=[POINT_1, POINT_2])
        append_points(config, extra_points)

        # assert a point has been added
        point_count = get_point_count(recipient_file_path)
        assert get_point_count(output_file) == point_count + 2

        # assert fields are the same
        fields_recipient = get_field_from_header(laspy.read(recipient_file_path))
        fields_output = get_field_from_header(laspy.read(output_file))
        assert set(fields_recipient) == set(fields_output)

        # assert all points are here
        las_recipient = laspy.read(recipient_file_path)
        las_output = laspy.read(output_file)
        for point in las_recipient.points[:10]:  # only 10 points, otherwise it takes too long
            assert point in las_output.points

        # add 1 point
        extra_points = pd.DataFrame(
            data=[
                POINT_1,
            ]
        )
        append_points(config, extra_points)

        # assert a point has been added
        point_count = get_point_count(recipient_file_path)
        assert get_point_count(output_file) == point_count + 1

        # # add 0 point
        extra_points = pd.DataFrame(data={"x": [], "y": [], "z": [], c.CLASSIFICATION_STR: []})
        append_points(config, extra_points)

        # assert a point has been added
        point_count = get_point_count(recipient_file_path)
        assert get_point_count(output_file) == point_count


def test_append_points_new_column(tmp_path_factory):
    tmp_file_dir = tmp_path_factory.mktemp("data")
    tmp_file_name = "result.laz"

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.RECIPIENT_DIRECTORY={RECIPIENT_TEST_DIR}",
                f"filepath.RECIPIENT_NAME={RECIPIENT_TEST_NAME}",
                f"filepath.OUTPUT_DIR={tmp_file_dir}",
                f"filepath.OUTPUT_NAME={tmp_file_name}",
                f"NEW_COLUMN={NEW_COLUMN}",
                f"NEW_COLUMN_SIZE={NEW_COLUMN_SIZE}",
                f"VALUE_ADDED_POINTS={VALUE_ADDED_POINTS}",
            ],
        )

        output_file = os.path.join(config.filepath.OUTPUT_DIR, config.filepath.OUTPUT_NAME)
        # add 2 points
        extra_points = pd.DataFrame(data=[POINT_1, POINT_2])
        append_points(config, extra_points)

        # assert a point has been added
        point_count = get_point_count(
            os.path.join(config.filepath.RECIPIENT_DIRECTORY, config.filepath.RECIPIENT_NAME)
        )
        assert get_point_count(output_file) == point_count + 2

        # assert the new column is here
        fields_output = get_field_from_header(laspy.read(output_file))
        assert NEW_COLUMN in fields_output

        # assert both points added, and only them, have NEW_COLUMN == VALUE_ADDED_POINTS
        las_output = laspy.read(output_file)
        new_column = las_output.points[NEW_COLUMN]
        assert new_column[-1] == VALUE_ADDED_POINTS
        assert new_column[-2] == VALUE_ADDED_POINTS
        assert max(new_column[:-2]) == 0


def test_get_donor_from_csv(tmp_path_factory):
    csv_file_path = tmp_path_factory.mktemp("csv") / "recipients_donors_links.csv"
    donor_more_fields_test_path = os.path.join(DONOR_MORE_FIELDS_TEST_DIR, DONOR_MORE_FIELDS_TEST_NAME)
    recipient_more_fields_test_path = os.path.join(RECIPIENT_TEST_DIR, RECIPIENT_TEST_NAME)
    data = {
        c.COORDINATES_KEY: [
            COORDINATES,
        ],
        c.DONOR_FILE_KEY: [
            donor_more_fields_test_path,
        ],
        c.RECIPIENT_FILE_KEY: [
            recipient_more_fields_test_path,
        ],
    }
    DataFrame(data=data).to_csv(csv_file_path)

    donor_file_path = get_donor_from_csv(recipient_more_fields_test_path, csv_file_path)
    assert donor_file_path == donor_more_fields_test_path


def test_get_donor_path(tmp_path_factory):
    # check get_donor_path when no csv
    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.DONOR_DIRECTORY={DONOR_TEST_DIR}",
                f"filepath.DONOR_NAME={DONOR_TEST_NAME}",
                f"filepath.RECIPIENT_DIRECTORY={RECIPIENT_SLIDED_TEST_DIR}",
                f"filepath.RECIPIENT_NAME={RECIPIENT_SLIDED_TEST_NAME}",
            ],
        )
        donor_dir, donor_name = get_donor_path(config)
        assert donor_dir == DONOR_TEST_DIR
        assert donor_name == DONOR_TEST_NAME

    # check get_donor_path when csv but no matching donor in it
    csv_file_dir = tmp_path_factory.mktemp("csv")
    csv_file_name = "recipients_donors_links.csv"
    csv_file_path = os.path.join(csv_file_dir, csv_file_name)

    data = {c.COORDINATES_KEY: [], c.DONOR_FILE_KEY: [], c.RECIPIENT_FILE_KEY: []}
    DataFrame(data=data).to_csv(csv_file_path)

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.DONOR_DIRECTORY={DONOR_TEST_DIR}",
                f"filepath.DONOR_NAME={DONOR_TEST_NAME}",
                f"filepath.RECIPIENT_DIRECTORY={RECIPIENT_SLIDED_TEST_DIR}",
                f"filepath.RECIPIENT_NAME={RECIPIENT_SLIDED_TEST_NAME}",
                f"filepath.CSV_DIRECTORY={csv_file_dir}",
                f"filepath.CSV_NAME={csv_file_name}",
            ],
        )

        donor_dir, donor_name = get_donor_path(config)
        assert donor_dir == ""
        assert donor_name == ""

    # check get_donor_path when csv but with a matching donor in it
    donor_more_fields_test_path = os.path.join(DONOR_MORE_FIELDS_TEST_DIR, DONOR_MORE_FIELDS_TEST_NAME)
    recipient_more_fields_test_path = os.path.join(RECIPIENT_TEST_DIR, RECIPIENT_TEST_NAME)
    data = {
        c.COORDINATES_KEY: [
            COORDINATES,
        ],
        c.DONOR_FILE_KEY: [
            donor_more_fields_test_path,
        ],
        c.RECIPIENT_FILE_KEY: [
            recipient_more_fields_test_path,
        ],
    }
    DataFrame(data=data).to_csv(csv_file_path)

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.DONOR_DIRECTORY={DONOR_TEST_DIR}",
                f"filepath.DONOR_NAME={DONOR_TEST_NAME}",
                f"filepath.RECIPIENT_DIRECTORY={RECIPIENT_TEST_DIR}",
                f"filepath.RECIPIENT_NAME={RECIPIENT_TEST_NAME}",
                f"filepath.CSV_DIRECTORY={csv_file_dir}",
                f"filepath.CSV_NAME={csv_file_name}",
            ],
        )

        donor_dir, donor_name = get_donor_path(config)
        assert donor_dir == DONOR_MORE_FIELDS_TEST_DIR
        assert donor_name == DONOR_MORE_FIELDS_TEST_NAME
