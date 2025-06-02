from pathlib import Path, PurePosixPath, PureWindowsPath

import geopandas as gpd
import pytest
from hydra import compose, initialize

import patchwork.path_manipulation as path_manipulation


def test_read_from_shapefile_with_windows_path():
    shp_path = "test/data/shapefile_mounted_windows_path/patchwork_geometries.shp"
    gdf = gpd.GeoDataFrame.from_file(shp_path, encoding="utf-8")
    assert PureWindowsPath(gdf["nuage_mixa"][0]) == PureWindowsPath(
        "\\\\store\\my-store\\test\\data\\aveyron_aval_lidarBD"
    )


def test_read_from_shapefile_with_unix_path():
    shp_path = "test/data/shapefile_mounted_unix_path/patchwork_geometries.shp"
    gdf = gpd.GeoDataFrame.from_file(shp_path, encoding="utf-8")
    assert PurePosixPath(gdf["nuage_mixa"][0]) == PurePosixPath("/store/my-store/test/data/aveyron_aval_lidarBD")


def test_read_from_config_file():
    with initialize(version_base="1.2", config_path="configs"):
        config = compose(
            config_name="config_test_mount_points.yaml",
            overrides=[],
        )
        assert PureWindowsPath(config.mount_points[0].ORIGINAL_PATH) == PureWindowsPath("\\\\store\\my-store")
        assert PurePosixPath(config.mount_points[1].ORIGINAL_PATH) == PurePosixPath("/store/my-store")


@pytest.mark.parametrize(
    "raw_path, mount_point, expected_output",
    [
        (  # Windows path with \\
            "\\\\store\\my-store\\my\\path",
            {
                "ORIGINAL_PLATFORM_IS_WINDOWS": True,
                "ORIGINAL_PATH": "\\\\store\\my-store\\",
                "MOUNTED_PATH": "/my/mounted/store",
            },
            Path("/my/mounted/store/my/path"),
        ),
        (  # Windows path with //
            "//store/my-store/my/path",
            {
                "ORIGINAL_PLATFORM_IS_WINDOWS": True,
                "ORIGINAL_PATH": "\\\\store\\my-store\\",
                "MOUNTED_PATH": "/my/mounted/store",
            },
            Path("/my/mounted/store/my/path"),
        ),
        (  # Unix path with
            "/store/my-store/my/path",
            {
                "ORIGINAL_PLATFORM_IS_WINDOWS": False,
                "ORIGINAL_PATH": "/store/my-store/",
                "MOUNTED_PATH": "/my/mounted/store",
            },
            Path("/my/mounted/store/my/path"),
        ),
        (  # Windows path that does not correspond to the store
            "\\\\store\\my-other-store\\my\\path",
            {
                "ORIGINAL_PLATFORM_IS_WINDOWS": True,
                "ORIGINAL_PATH": "\\\\store\\my-store\\",
                "MOUNTED_PATH": "/my/mounted/store",
            },
            None,
        ),
    ],
)
def test_get_mounted_path_from_mount_point(raw_path, mount_point, expected_output):
    mounted_path = path_manipulation.get_mounted_path_from_mount_point(raw_path, mount_point)
    assert mounted_path == expected_output


@pytest.mark.parametrize(
    "raw_path, expected_output",
    [
        # Path in first store
        ("//store/my-windows-store-1/my/path", Path("/my/mounted/store-1/my/path")),
        # Path in second store's root
        ("//store/my-windows-store-2", Path("/my/mounted/store-2")),
        # Path in third store
        ("/store/my-unix-store/", Path("/my/mounted/unix-store")),
        # Path in no store
        ("/my/path/from/no/store/", Path("/my/path/from/no/store/")),
    ],
)
def test_get_mounted_path_from_raw_path(raw_path, expected_output):
    mount_points = [
        {
            "ORIGINAL_PLATFORM_IS_WINDOWS": True,
            "ORIGINAL_PATH": "\\\\store\\my-windows-store-1\\",
            "MOUNTED_PATH": "/my/mounted/store-1",
        },
        {
            "ORIGINAL_PLATFORM_IS_WINDOWS": True,
            "ORIGINAL_PATH": "\\\\store\\my-windows-store-2\\",
            "MOUNTED_PATH": "/my/mounted/store-2",
        },
        {
            "ORIGINAL_PLATFORM_IS_WINDOWS": False,
            "ORIGINAL_PATH": "/store/my-unix-store/",
            "MOUNTED_PATH": "/my/mounted/unix-store",
        },
    ]
    mounted_path = path_manipulation.get_mounted_path_from_raw_path(raw_path, mount_points)
    assert mounted_path == expected_output


def test_get_mounted_path_from_raw_path_no_mount_point():
    mount_points = []
    raw_path = "/my/path"
    mounted_path = path_manipulation.get_mounted_path_from_raw_path(raw_path, mount_points)
    assert mounted_path == Path(raw_path)
