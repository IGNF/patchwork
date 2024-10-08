import os
import shutil
import pathlib
# import logging
import timeit

import hydra
from omegaconf import DictConfig
import geopandas as gpd
import laspy
from laspy import ScaleAwarePointRecord
from shapely import box
import numpy as np
from shapely.geometry import MultiPolygon
from shapely.vectorized import contains
from loguru import logger

import constants as c
from tools import identify_bounds, get_tile_origin_from_pointcloud, crop_tile


@hydra.main(config_path="configs/", config_name="configs_patchwork.yaml", version_base="1.2")
def patchwork_dispatcher(config: DictConfig):
    # preparing donor files:
    select_lidar(config,
                 config.filepath.DONOR_DIRECTORY,
                 config.filepath.OUTPUT_DIRECTORY_PATH,
                 c.DONOR_SUBDIRECTORY_NAME,
                 True
                 )
    # preparing recipient files:
    select_lidar(config,
                 config.filepath.RECIPIENT_DIRECTORY,
                 config.filepath.OUTPUT_DIRECTORY_PATH,
                 c.RECIPIENT_SUBDIRECTORY_NAME,
                 False,
                 )


def cut_lidar(las_points: ScaleAwarePointRecord, shapefile_geometry: MultiPolygon) -> ScaleAwarePointRecord:
    shapefile_contains_mask = contains(shapefile_geometry, np.array(las_points['x']), np.array(las_points['y']))
    return las_points[shapefile_contains_mask]


def select_lidar(config: DictConfig, input_directory, output_directory, subdirectory_name, to_be_cut):
    """
    Walk the input directory searching for las files, and pick the ones that intersect with the shapefile.
    When a las file is half inside the shapfile, it is cut if "to_be_cut" is true, otherwise it kept whole
    The results are put in: output_directory/XXXX_YYYY/subdirectory_name, where XXXX_YYYY is
    the north west corner of the file
    """

    worksite = gpd.GeoDataFrame.from_file(config.filepath.SHAPEFILE_PATH)
    shapefile_geometry = worksite.dissolve().geometry.item()

    time_old = timeit.default_timer()
    time_start = time_old
    for root, _, file_names in os.walk(input_directory):

        for file_name in file_names:
            if not file_name.endswith((".las", ".laz")):
                continue

            logger.info(f"Processing : {file_name}")
            las_path = os.path.join(root, file_name)
            with laspy.open(las_path) as las_file:
                raw_las_points = las_file.read().points
                min_x, max_x, min_y, max_y = identify_bounds(config.TILE_SIZE, raw_las_points)
                intersect_area = shapefile_geometry.intersection(box(min_x, min_y, max_x, max_y)).area

                # if intersect area == 0, this tile is fully outside the shapefile
                if intersect_area == 0:

                    time_new = timeit.default_timer()
                    delta_time = round(time_new - time_old, 2)
                    logger.info(f"Processed {file_name} (out) in {delta_time} sec")
                    time_old = time_new
                    continue

                las_points = crop_tile(config, raw_las_points)
                x_corner, y_corner = get_tile_origin_from_pointcloud(config, las_points)
                corner_string = f"{int(x_corner/1000)}_{int(y_corner/1000)}"
                directory_path = os.path.join(output_directory, corner_string, subdirectory_name)
                pathlib.Path(directory_path).mkdir(parents=True, exist_ok=True)

                # if intersect area == TILE_SIZE², this tile is fully inside the shapefile
                if intersect_area >= config.TILE_SIZE * config.TILE_SIZE or not to_be_cut:
                    shutil.copyfile(las_path, os.path.join(directory_path, file_name))

                    time_new = timeit.default_timer()
                    delta_time = round(time_new - time_old, 2)
                    logger.info(f"Processed {file_name} (in) in {delta_time} sec")
                    time_old = time_new
                    continue

                # else, this tile is partially inside the shapefile, we have to cut it
                points_in_geometry = cut_lidar(las_points, shapefile_geometry)

                # save the selected points to as file
                cut_las_path = os.path.join(directory_path, file_name)
                with laspy.open(cut_las_path, mode="w", header=las_file.header) as writer:
                    writer.write_points(points_in_geometry)

                time_new = timeit.default_timer()
                delta_time = round(time_new - time_old, 2)
                logger.info(f"Processed {file_name} (cut) in {delta_time} sec")
                time_old = time_new

    time_end = timeit.default_timer()
    delta_time = round(time_end - time_start, 2)
    logger.info(f"Finished processing in {delta_time} sec")


if __name__ == "__main__":
    patchwork_dispatcher()
