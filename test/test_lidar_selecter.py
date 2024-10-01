import sys

import laspy
from hydra import compose, initialize
from shapely.geometry import MultiPolygon
import numpy as np
import geopandas as gpd

sys.path.append('../patchwork')

from lidar_selecter import cut_lidar, select_lidar


CRS = 2154
TILE_SIZE = 1000
SHAPE_CORNER_1 = (0, 0)
SHAPE_CORNER_2 = (1000, 0)
SHAPE_CORNER_3 = (1000, 1000)

POINT_INSIDE_1 = (750, 500, 1)
POINT_INSIDE_2 = (500, 250, 2)
POINT_OUTSIDE_1 = (500, 750, 3)
POINT_OUTSIDE_2 = (250, 500, 4)

INPUT_DIRECTORY = "las"
OUTPUT_DIRECTORY = "output_directory"
SUBDIRECTORY_NAME = "test"
LASFILE_NAME = "las.las"


def test_cut_lidar():
    shapefile_geometry = MultiPolygon([([SHAPE_CORNER_1, SHAPE_CORNER_2, SHAPE_CORNER_3],),])
    las_points = np.array([POINT_INSIDE_1, POINT_INSIDE_2, POINT_OUTSIDE_1, POINT_OUTSIDE_2],
                          dtype=[('x', 'float32'), ('y', 'float32'), ('z', 'float32')]
                          )
    points_in_geometry = cut_lidar(las_points, shapefile_geometry)
    list_points_in_geometry = points_in_geometry.tolist()
    assert POINT_INSIDE_1 in list_points_in_geometry
    assert POINT_INSIDE_2 in list_points_in_geometry
    assert POINT_OUTSIDE_1 not in list_points_in_geometry
    assert POINT_OUTSIDE_2 not in list_points_in_geometry


def test_select_lidar(tmp_path_factory):
    # shapefile creation
    shapefile_path = tmp_path_factory.mktemp("shapefile") / "shapefile.shp"
    shapefile_geometry = MultiPolygon([([SHAPE_CORNER_1, SHAPE_CORNER_2, SHAPE_CORNER_3],),])
    gpd_shapefile_geometry = gpd.GeoDataFrame({'geometry': [shapefile_geometry]}, crs=CRS)
    gpd_shapefile_geometry.to_file(shapefile_path)

    # las creation
    input_directory = tmp_path_factory.mktemp(INPUT_DIRECTORY)
    las_path = input_directory / LASFILE_NAME

    las = laspy.LasData(laspy.LasHeader(point_format=3, version="1.4"))
    las_points = np.array([POINT_INSIDE_1, POINT_INSIDE_2, POINT_OUTSIDE_1, POINT_OUTSIDE_2],
                          dtype=[('x', 'float32'), ('y', 'float32'), ('z', 'float32')]
                          )

    las.x = las_points['x']
    las.y = las_points['y']
    las.z = las_points['z']

    las.write(las_path)

    # create output directory
    output_directory = las_path = tmp_path_factory.mktemp(OUTPUT_DIRECTORY)

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"cutter.SHAPEFILE_PATH={shapefile_path}",
                f"TILE_SIZE={TILE_SIZE}"
            ]
        )
        subdirectory_name = SUBDIRECTORY_NAME
        select_lidar(config, input_directory, output_directory, subdirectory_name)

    output_las_path = output_directory / "0_1" / subdirectory_name / LASFILE_NAME
    with laspy.open(output_las_path) as las_file:
        raw_las_points = las_file.read().points
        x = raw_las_points.x
        y = raw_las_points.y
        z = raw_las_points.z

        las_points_list = list(zip(x, y, z))

        assert POINT_INSIDE_1 in las_points_list
        assert POINT_INSIDE_2 in las_points_list
        assert POINT_OUTSIDE_1 not in las_points_list
        assert POINT_OUTSIDE_2 not in las_points_list
