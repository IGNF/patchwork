import pytest

from patchwork.shapefile_data_extraction import get_donor_info_from_shapefile

INPUT_SHP_PATH = "test/data/shapefile_local/patchwork_geometries.shp"
DONOR_SUBDIRECTORY = "data"
MOUNT_POINTS = [
    {
        "ORIGINAL_PLATFORM_IS_WINDOWS": True,
        "ORIGINAL_PATH": "\\\\store\\my-store\\",
        "MOUNTED_PATH": "/my/mounted/windows/store",
    },
    {
        "ORIGINAL_PLATFORM_IS_WINDOWS": False,
        "ORIGINAL_PATH": "/store/my-store/",
        "MOUNTED_PATH": "/my/mounted/unix/store",
    },
]


@pytest.mark.parametrize(
    "x,y, expected_full_path",
    [
        (
            673,
            6362,
            {"test/data/aveyron_aval_lidarBD/data/NUALID_1-0_VLIDAVEYRONAVAL_PTS_0673_6362_LAMB93_IGN69_20210319.laz"},
        ),  # Expect only one output file
        (
            673,
            6363,
            {
                "test/data/aveyron_aval_lidarBD/data/NUALID_1-0_VLIDAVEYRONAVAL_PTS_0673_6363_LAMB93_IGN69_20210319.laz",  # noqa: E501
                "test/data/aveyron_lidarBD/data/NUALID_1-0_IAVEY_PTS_0673_6363_LAMB93_IGN69_20170519.laz",
            },
        ),  # Expect 2 output files
        (673, 6365, set()),  # Expect no output file
        (
            673,
            6362,
            {"test/data/aveyron_aval_lidarBD/data/NUALID_1-0_VLIDAVEYRONAVAL_PTS_0673_6362_LAMB93_IGN69_20210319.laz"},
        ),  # Expect only one output file
    ],
)
def test_get_donor_info_from_shapefile(x, y, expected_full_path):
    gdf = get_donor_info_from_shapefile(INPUT_SHP_PATH, x, y, DONOR_SUBDIRECTORY, [])
    # Check that all paths are filled
    assert set(gdf.columns) == {"x", "y", "full_path", "geometry"}
    assert len(gdf.index) == len(expected_full_path)
    assert set(gdf["full_path"]) == expected_full_path


@pytest.mark.parametrize(
    "input_shp, x, y, error_type",
    [
        (
            "test/data/shapefiles_nok/patchwork_geometries_coord_not_in_all_names.shp",
            673,
            6362,
            NotImplementedError,
        ),
        (
            "test/data/shapefiles_nok/patchwork_geometries_path_does_not_exist.shp",
            673,
            6363,
            FileNotFoundError,
        ),
        (
            "test/data/shapefiles_nok/patchwork_geometries_no_match_for_las_tile.shp",
            673,
            6365,
            FileNotFoundError,
        ),  # Tile described in shapefile but not found in directory
        (
            "test/data/shapefiles_nok/patchwork_geometries_several_matches_for_las_tile.shp",
            673,
            6363,
            RuntimeError,
        ),
    ],
)
def test_get_donor_info_from_shapefile_raise_error(input_shp, x, y, error_type):
    with pytest.raises(error_type):
        get_donor_info_from_shapefile(input_shp, x, y, DONOR_SUBDIRECTORY, [])


@pytest.mark.parametrize(
    "input_shp_path, x,y, expected_lookup_directory",
    [
        (
            "test/data/shapefile_mounted_unix_path/patchwork_geometries.shp",
            673,
            6362,
            "/my/mounted/unix/store/test/data/aveyron_aval_lidarBD/data",
        ),  # Expect only one output file with unix path
        (
            "test/data/shapefile_mounted_windows_path/patchwork_geometries.shp",
            673,
            6363,
            "/my/mounted/windows/store/test/data/aveyron_aval_lidarBD/data",  # noqa: E501            },
        ),  # Expect one output file with windows path
    ],
)
def test_get_donor_info_from_shapefile_with_mount_points_check_lookup_directory(
    input_shp_path, x, y, expected_lookup_directory
):
    with pytest.raises(FileNotFoundError, match=f"Directory {expected_lookup_directory} not found"):
        get_donor_info_from_shapefile(input_shp_path, x, y, DONOR_SUBDIRECTORY, MOUNT_POINTS)


@pytest.mark.parametrize(
    "input_shp_path",
    [
        "test/data/shapefile_mounted_windows_path/patchwork_geometries.shp",
        # Expect no output file with windows paths
        "test/data/shapefile_mounted_unix_path/patchwork_geometries.shp",  # Expect no output file with unix paths
    ],
)
def test_get_donor_info_from_shapefile_with_mount_points_no_path(input_shp_path):
    x = 673
    y = 6365
    expected_full_path = set()
    gdf = get_donor_info_from_shapefile(input_shp_path, x, y, DONOR_SUBDIRECTORY, MOUNT_POINTS)
    # Check that all paths are filled
    assert set(gdf.columns) == {"x", "y", "full_path", "geometry"}
    assert len(gdf.index) == len(expected_full_path)
    assert set(gdf["full_path"]) == expected_full_path
