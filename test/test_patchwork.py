import os

import geopandas as gpd
import laspy
import numpy as np
import pandas as pd
import pytest
from hydra import compose, initialize
from pdaltools.las_info import get_tile_origin_using_header_info

import patchwork.constants as c
from patchwork.patchwork import (
    append_points,
    get_complementary_points,
    get_field_from_header,
    get_selected_classes_points,
    get_type,
    patchwork,
)

TEST_DATA_DIR = "test/data/"
RECIPIENT_TEST_NAME = "recipient_test.laz"

DONOR_CLASS_LIST = [2, 9]
RECIPIENT_CLASS_LIST = [2, 3, 9, 17]
VIRTUAL_CLASS_TRANSLATION = {2: 69, 9: 70}
POINT_1 = {"x": 1, "y": 2, "z": 3, c.CLASSIFICATION_STR: 4}
POINT_2 = {"x": 5, "y": 6, "z": 7, c.CLASSIFICATION_STR: 8}
NEW_COLUMN = "virtual_column"
NEW_COLUMN_SIZE = 8
VALUE_ADDED_POINTS = 1
TILE_SIZE = 1000
PATCH_SIZE = 1

SHP_X_Y_TO_METER_FACTOR = 1000


def test_get_field_from_header():
    with laspy.open(os.path.join(TEST_DATA_DIR, RECIPIENT_TEST_NAME)) as recipient_file:
        recipient_fields_list = get_field_from_header(recipient_file)
        assert len(recipient_fields_list) == 18
        # check if all fields are lower case
        assert [field for field in recipient_fields_list if field != field.lower()] == []


@pytest.mark.parametrize(
    "las_path, class_list, fields_to_keep, use_synthetic",
    [
        # Keep all points
        (os.path.join(TEST_DATA_DIR, RECIPIENT_TEST_NAME), [1, 2, 3, 4, 5], ["synthetic", "intensity"], True),
        # Filter on class only
        (os.path.join(TEST_DATA_DIR, RECIPIENT_TEST_NAME), [2, 3], ["synthetic", "intensity"], True),
        # Filter out synthetic points
        (os.path.join(TEST_DATA_DIR, RECIPIENT_TEST_NAME), [2, 3], ["synthetic", "x"], False),
    ],
)
def test_get_selected_classes_points(las_path, class_list, fields_to_keep, use_synthetic):
    tile_origin = get_tile_origin_using_header_info(las_path, TILE_SIZE)
    with laspy.open(las_path) as recipient_file:
        input_points = recipient_file.read().points
        df_output_points = get_selected_classes_points(
            tile_origin,
            input_points,
            class_list,
            fields_to_keep=fields_to_keep,
            use_synthetic_points=use_synthetic,
            patch_size=PATCH_SIZE,
            tile_size=TILE_SIZE,
        )
        assert len(df_output_points.index), "No points in output dataframe"
        classification = set(df_output_points[c.CLASSIFICATION_STR])
        assert classification.issubset(class_list)
        assert set(df_output_points.columns.values) == {
            *fields_to_keep,
            c.PATCH_X_STR,
            c.PATCH_Y_STR,
            c.CLASSIFICATION_STR,
        }
        if use_synthetic:
            assert len(df_output_points.index) == np.count_nonzero(
                np.isin(np.array(input_points.classification), class_list)
            )
        else:
            assert not np.any(df_output_points.synthetic)


def test_get_selected_classes_points_raise_error():
    las_path = os.path.join(TEST_DATA_DIR, "recipient_with_synthetic_points.laz")
    class_list = [2, 3]
    fields_to_keep = []
    use_synthetic = False
    tile_origin = get_tile_origin_using_header_info(las_path, TILE_SIZE)
    with pytest.raises(NotImplementedError):
        with laspy.open(las_path) as las_path:
            input_points = las_path.read().points
            get_selected_classes_points(
                tile_origin,
                input_points,
                class_list,
                fields_to_keep=fields_to_keep,
                use_synthetic_points=use_synthetic,
                patch_size=PATCH_SIZE,
                tile_size=TILE_SIZE,
            )


@pytest.mark.parametrize(
    "donor_info_path, recipient_path, x, y, expected_nb_points",
    # expected_nb_points value set after inspection of the initial result using qgis:
    # - there are points only inside the shapefile geometry
    # - when visualizing a grid, there seems to be no points in the cells where there is ground points in the
    # recipient laz
    [
        (
            "test/data/donor_infos/donor_info_673_6362_one_donor.csv",
            "test/data/lidar_HD_decimated/Semis_2022_0673_6362_LA93_IGN69_decimated.laz",
            673,
            6362,
            128675,
        ),
        (
            "test/data/donor_infos/donor_info_673_6363_two_donors.csv",
            "test/data/lidar_HD_decimated/Semis_2022_0673_6363_LA93_IGN69_decimated.laz",
            673,
            6363,
            149490,
        ),
        (
            "test/data/donor_infos/donor_info_674_6363_no_donor.csv",
            "test/data/lidar_HD_decimated/Semis_2022_0674_6363_LA93_IGN69_decimated.laz",
            674,
            6363,
            0,
        ),
    ],
)
def test_get_complementary_points(donor_info_path, recipient_path, x, y, expected_nb_points):
    df = pd.read_csv(donor_info_path, encoding="utf-8")
    s = gpd.GeoSeries.from_wkt(df.geometry)
    df_donor_info = gpd.GeoDataFrame(data=df, geometry=s)

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"DONOR_CLASS_LIST={DONOR_CLASS_LIST}",
                f"RECIPIENT_CLASS_LIST={RECIPIENT_CLASS_LIST}",
                f"+VIRTUAL_CLASS_TRANSLATION={VIRTUAL_CLASS_TRANSLATION}",
                "DONOR_USE_SYNTHETIC_POINTS=true",
            ],
        )
        complementary_points = get_complementary_points(df_donor_info, recipient_path, (x, y), config)

    assert np.all(complementary_points["x"] >= x * SHP_X_Y_TO_METER_FACTOR)
    assert np.all(complementary_points["x"] <= (x + 1) * SHP_X_Y_TO_METER_FACTOR)
    assert np.all(complementary_points["y"] >= (y - 1) * SHP_X_Y_TO_METER_FACTOR)
    assert np.all(complementary_points["y"] <= y * SHP_X_Y_TO_METER_FACTOR)

    assert len(complementary_points.index) == expected_nb_points


def test_get_complementary_points_2_more_fields(tmp_path_factory):
    """test selected_classes_points with more fields in files, different from each other's"""
    original_recipient_path = "test/data/lidar_HD_decimated/Semis_2022_0673_6362_LA93_IGN69_decimated.laz"
    original_donor_path = (
        "test/data/aveyron_aval_lidarBD/data/NUALID_1-0_VLIDAVEYRONAVAL_PTS_0673_6362_LAMB93_IGN69_20210319.laz"
    )
    original_donor_info_path = "test/data/donor_infos/donor_info_673_6362_one_donor.csv"
    x = 673
    y = 6362

    tmp_dir = tmp_path_factory.mktemp("data")
    tmp_recipient_name = "recipient_with_extra_dims.laz"
    tmp_recipient_path = os.path.join(tmp_dir, tmp_recipient_name)

    tmp_donor_name = "donor_with_extra_dims.laz"
    tmp_donor_path = os.path.join(tmp_dir, tmp_donor_name)

    df = pd.read_csv(original_donor_info_path, encoding="utf-8")
    s = gpd.GeoSeries.from_wkt(df.geometry)
    df_donor_info = gpd.GeoDataFrame(data=df, geometry=s)
    df_donor_info["full_path"] = [tmp_donor_path]

    extra_fields_for_recipient = ["f1", "f2"]
    las = laspy.read(original_recipient_path)
    for field in extra_fields_for_recipient:
        las.add_extra_dim(laspy.ExtraBytesParams(name=field, type=np.uint64))
    las.write(tmp_recipient_path)

    extra_fields_for_donor = ["f3", "f4"]
    las = laspy.read(original_donor_path)
    for field in extra_fields_for_donor:
        las.add_extra_dim(laspy.ExtraBytesParams(name=field, type=np.uint64))
    las.write(tmp_donor_path)

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"DONOR_CLASS_LIST={DONOR_CLASS_LIST}",
                f"RECIPIENT_CLASS_LIST={RECIPIENT_CLASS_LIST}",
                f"+VIRTUAL_CLASS_TRANSLATION={VIRTUAL_CLASS_TRANSLATION}",
                "DONOR_USE_SYNTHETIC_POINTS=true",
            ],
        )

        complementary_points = get_complementary_points(df_donor_info, tmp_recipient_path, (x, y), config)

    assert len(complementary_points.index) == 128675
    columns = complementary_points.columns
    for field in extra_fields_for_recipient:  # no extra field from the recipient should exist
        assert field not in columns
    for field in extra_fields_for_donor:  # every extra field from the donor should exist...
        assert field in columns
        assert complementary_points[field].all() == 0  # ...but should be at 0


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
                f"filepath.RECIPIENT_DIRECTORY={TEST_DATA_DIR}",
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
                f"filepath.RECIPIENT_DIRECTORY={TEST_DATA_DIR}",
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


@pytest.mark.parametrize(
    "recipient_path, expected_nb_added_points",
    # expected_nb_points value set after inspection of the initial result using qgis:
    # - there are points only inside the shapefile geometry
    # - when visualizing a grid, there seems to be no points in the cells where there is ground points in the
    # recipient laz
    [
        (
            "test/data/lidar_HD_decimated/Semis_2022_0673_6362_LA93_IGN69_decimated.laz",
            128675,
        ),  # One donor
        (
            "test/data/lidar_HD_decimated/Semis_2022_0673_6363_LA93_IGN69_decimated.laz",
            149490,
        ),  # Two donors
        (
            "test/data/lidar_HD_decimated/Semis_2022_0674_6363_LA93_IGN69_decimated.laz",
            0,
        ),  # No donor
    ],
)
def test_patchwork_default(tmp_path_factory, recipient_path, expected_nb_added_points):
    input_shp_path = "test/data/shapefile_local/patchwork_geometries.shp"
    tmp_file_dir = tmp_path_factory.mktemp("data")
    tmp_output_las_name = "result_patchwork.laz"
    tmp_output_indices_map_name = "result_patchwork_indices.tif"

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.RECIPIENT_DIRECTORY={os.path.dirname(recipient_path)}",
                f"filepath.RECIPIENT_NAME={os.path.basename(recipient_path)}",
                f"filepath.SHP_DIRECTORY={os.path.dirname(input_shp_path)}",
                f"filepath.SHP_NAME={os.path.basename(input_shp_path)}",
                f"filepath.OUTPUT_DIR={tmp_file_dir}",
                f"filepath.OUTPUT_NAME={tmp_output_las_name}",
                f"filepath.OUTPUT_INDICES_MAP_DIR={tmp_file_dir}",
                f"filepath.OUTPUT_INDICES_MAP_NAME={tmp_output_indices_map_name}",
                f"DONOR_CLASS_LIST={DONOR_CLASS_LIST}",
                f"RECIPIENT_CLASS_LIST={RECIPIENT_CLASS_LIST}",
                f"+VIRTUAL_CLASS_TRANSLATION={VIRTUAL_CLASS_TRANSLATION}",
                "DONOR_USE_SYNTHETIC_POINTS=true",
                "NEW_COLUMN=null",
            ],
        )
        patchwork(config)
        output_path = os.path.join(tmp_file_dir, tmp_output_las_name)
        indices_map_path = os.path.join(tmp_file_dir, tmp_output_indices_map_name)
        assert os.path.isfile(output_path)
        assert os.path.isfile(indices_map_path)

        with laspy.open(recipient_path) as las_file:
            recipient_points = las_file.read().points
        with laspy.open(output_path) as las_file:
            output_points = las_file.read().points
            assert {n for n in las_file.header.point_format.dimension_names} == {
                n for n in las_file.header.point_format.standard_dimension_names
            }
        assert len(output_points) == len(recipient_points) + expected_nb_added_points


@pytest.mark.parametrize(
    "recipient_path, donor_use_synthetic_points, expected_nb_added_points",
    # expected_nb_points value set after inspection of the initial result using qgis:
    # - there are points only inside the shapefile geometry
    # - when visualizing a grid, there seems to be no points in the cells where there is ground points in the
    # recipient laz
    [
        (
            "test/data/lidar_HD_decimated/Semis_2022_0673_6362_LA93_IGN69_decimated.laz",
            True,
            128675,
        ),  # One donor
        (
            "test/data/lidar_HD_decimated/Semis_2022_0673_6362_LA93_IGN69_decimated.laz",
            False,
            127961,
        ),  # One donor, no synthetic points
        (
            "test/data/lidar_HD_decimated/Semis_2022_0673_6363_LA93_IGN69_decimated.laz",
            True,
            149490,
        ),  # Two donors
        (
            "test/data/lidar_HD_decimated/Semis_2022_0673_6363_LA93_IGN69_decimated.laz",
            False,
            149340,
        ),  # Two donors, no synthetic points
        (
            "test/data/lidar_HD_decimated/Semis_2022_0674_6363_LA93_IGN69_decimated.laz",
            True,
            0,
        ),  # No donor
    ],
)
def test_patchwork_with_origin(tmp_path_factory, recipient_path, donor_use_synthetic_points, expected_nb_added_points):
    input_shp_path = "test/data/shapefile_local/patchwork_geometries.shp"
    tmp_file_dir = tmp_path_factory.mktemp("data")
    tmp_output_las_name = "result_patchwork.laz"
    tmp_output_indices_map_name = "result_patchwork_indices.tif"

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"filepath.RECIPIENT_DIRECTORY={os.path.dirname(recipient_path)}",
                f"filepath.RECIPIENT_NAME={os.path.basename(recipient_path)}",
                f"filepath.SHP_DIRECTORY={os.path.dirname(input_shp_path)}",
                f"filepath.SHP_NAME={os.path.basename(input_shp_path)}",
                f"filepath.OUTPUT_DIR={tmp_file_dir}",
                f"filepath.OUTPUT_NAME={tmp_output_las_name}",
                f"filepath.OUTPUT_INDICES_MAP_DIR={tmp_file_dir}",
                f"filepath.OUTPUT_INDICES_MAP_NAME={tmp_output_indices_map_name}",
                f"DONOR_CLASS_LIST={DONOR_CLASS_LIST}",
                f"RECIPIENT_CLASS_LIST={RECIPIENT_CLASS_LIST}",
                f"DONOR_USE_SYNTHETIC_POINTS={donor_use_synthetic_points}",
                "NEW_COLUMN='Origin'",
            ],
        )
        patchwork(config)
        output_path = os.path.join(tmp_file_dir, tmp_output_las_name)
        indices_map_path = os.path.join(tmp_file_dir, tmp_output_indices_map_name)
        assert os.path.isfile(output_path)
        assert os.path.isfile(indices_map_path)

        with laspy.open(recipient_path) as las_file:
            recipient_points = las_file.read().points
        with laspy.open(output_path) as las_file:
            output_points = las_file.read().points
            assert {n for n in las_file.header.point_format.dimension_names} == {
                n for n in las_file.header.point_format.standard_dimension_names
            } | {"Origin"}

        assert len(output_points) == len(recipient_points) + expected_nb_added_points
        assert np.sum(output_points.Origin == 0) == len(recipient_points)
        assert np.sum(output_points.Origin == 1) == expected_nb_added_points


@pytest.mark.parametrize(
    "input_shp_path, recipient_path, expected_nb_added_points",
    # Same tests as "test_patchwork_default", but with shapefiles that refer to paths in mounted stores
    # All tests keep synthetic points
    [
        (
            "test/data/shapefile_mounted_unix_path/patchwork_geometries.shp",
            "test/data/lidar_HD_decimated/Semis_2022_0673_6362_LA93_IGN69_decimated.laz",
            128675,
        ),  # One donor / unix paths
        (
            "test/data/shapefile_mounted_unix_path/patchwork_geometries.shp",
            "test/data/lidar_HD_decimated/Semis_2022_0673_6363_LA93_IGN69_decimated.laz",
            149490,
        ),  # Two donors / unix paths
        (
            "test/data/shapefile_mounted_unix_path/patchwork_geometries.shp",
            "test/data/lidar_HD_decimated/Semis_2022_0674_6363_LA93_IGN69_decimated.laz",
            0,
        ),  # No donor / unix paths
        (
            "test/data/shapefile_mounted_windows_path/patchwork_geometries.shp",
            "test/data/lidar_HD_decimated/Semis_2022_0673_6362_LA93_IGN69_decimated.laz",
            128675,
        ),  # One donor / windows paths
        (
            "test/data/shapefile_mounted_windows_path/patchwork_geometries.shp",
            "test/data/lidar_HD_decimated/Semis_2022_0673_6363_LA93_IGN69_decimated.laz",
            149490,
        ),  # Two donors / windows paths
        (
            "test/data/shapefile_mounted_windows_path/patchwork_geometries.shp",
            "test/data/lidar_HD_decimated/Semis_2022_0674_6363_LA93_IGN69_decimated.laz",
            0,
        ),  # No donor / windows paths
    ],
)
def test_patchwork_with_mount_points(tmp_path_factory, input_shp_path, recipient_path, expected_nb_added_points):
    tmp_file_dir = tmp_path_factory.mktemp("data")
    tmp_output_las_name = "result_patchwork.laz"
    tmp_output_indices_map_name = "result_patchwork_indices.tif"

    with initialize(version_base="1.2", config_path="configs"):  # Use configs dir from test directory
        config = compose(
            config_name="config_test_mount_points.yaml",
            overrides=[
                f"filepath.RECIPIENT_DIRECTORY={os.path.dirname(recipient_path)}",
                f"filepath.RECIPIENT_NAME={os.path.basename(recipient_path)}",
                f"filepath.SHP_DIRECTORY={os.path.dirname(input_shp_path)}",
                f"filepath.SHP_NAME={os.path.basename(input_shp_path)}",
                f"filepath.OUTPUT_DIR={tmp_file_dir}",
                f"filepath.OUTPUT_NAME={tmp_output_las_name}",
                f"filepath.OUTPUT_INDICES_MAP_DIR={tmp_file_dir}",
                f"filepath.OUTPUT_INDICES_MAP_NAME={tmp_output_indices_map_name}",
                f"DONOR_CLASS_LIST={DONOR_CLASS_LIST}",
                f"RECIPIENT_CLASS_LIST={RECIPIENT_CLASS_LIST}",
                "NEW_COLUMN='Origin'",
            ],
        )
        patchwork(config)
        output_path = os.path.join(tmp_file_dir, tmp_output_las_name)
        indices_map_path = os.path.join(tmp_file_dir, tmp_output_indices_map_name)
        assert os.path.isfile(output_path)
        assert os.path.isfile(indices_map_path)

        with laspy.open(recipient_path) as las_file:
            recipient_points = las_file.read().points
        with laspy.open(output_path) as las_file:
            output_points = las_file.read().points
            assert {n for n in las_file.header.point_format.dimension_names} == {
                n for n in las_file.header.point_format.standard_dimension_names
            } | {"Origin"}

        assert len(output_points) == len(recipient_points) + expected_nb_added_points
        assert np.sum(output_points.Origin == 0) == len(recipient_points)
        assert np.sum(output_points.Origin == 1) == expected_nb_added_points
