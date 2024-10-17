import os
import pathlib
import timeit

import hydra
from omegaconf import DictConfig
import geopandas as gpd
import laspy
from laspy import ScaleAwarePointRecord
from shapely import box
import numpy as np
from pandas import DataFrame
from shapely.geometry import MultiPolygon
from shapely.vectorized import contains
from loguru import logger

import constants as c
from tools import identify_bounds, get_tile_origin_from_pointcloud, crop_tile


@hydra.main(config_path="configs/", config_name="configs_patchwork.yaml", version_base="1.2")
def patchwork_dispatcher(config: DictConfig):
    data = {c.COORDINATES_KEY: [],
            c.DONOR_FILE_KEY: [],
            c.RECIPIENT_FILE_KEY: []
            }
    df_result = DataFrame(data=data)
    # preparing donor files:
    select_lidar(config,
                 config.filepath.DONOR_DIRECTORY,
                 config.filepath.OUTPUT_DIRECTORY_PATH,
                 c.DONOR_SUBDIRECTORY_NAME,
                 df_result,
                 c.DONOR_FILE_KEY,
                 True
                 )
    # preparing recipient files:
    select_lidar(config,
                 config.filepath.RECIPIENT_DIRECTORY,
                 config.filepath.OUTPUT_DIRECTORY_PATH,
                 c.RECIPIENT_SUBDIRECTORY_NAME,
                 df_result,
                 c.RECIPIENT_FILE_KEY,
                 False,
                 )
    
    df_result.to_csv(config.filepath.CSV_PATH, index=False) 


def cut_lidar(las_points: ScaleAwarePointRecord, shapefile_geometry: MultiPolygon) -> ScaleAwarePointRecord:
    shapefile_contains_mask = contains(shapefile_geometry, np.array(las_points['x']), np.array(las_points['y']))
    return las_points[shapefile_contains_mask]


def update_df_result(df_result: DataFrame, df_key: str, corner_string: str, file_path: str):
    # corner_string not yet in df_result
    if not corner_string in list(df_result[c.COORDINATES_KEY]):
        new_row = {c.COORDINATES_KEY:corner_string, c.DONOR_FILE_KEY: "", c.RECIPIENT_FILE_KEY:""}
        new_row[df_key] = file_path
        df_result.loc[len(df_result)] = new_row
        return df_result

    # corner_string already in df_result
    df_result.loc[df_result[c.COORDINATES_KEY] == corner_string, df_key] = file_path
    return df_result


def select_lidar(config: DictConfig,
                 input_directory:str,
                 output_directory:str,
                 subdirectory_name: str,
                 df_result:DataFrame,
                 df_key: str,
                 to_be_cut: bool):
    """
    Walk the input directory searching for las files, and pick the ones that intersect with the shapefile.
    When a las file is half inside the shapfile, it is cut if "to_be_cut" is true, otherwise it kept whole
    If a file is cut, the cut file is put in: output_directory/subdirectory_name
    Finally, df_result is updated with the path for each file
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

                directory_path = os.path.join(output_directory, subdirectory_name)
                pathlib.Path(directory_path).mkdir(parents=True, exist_ok=True)

                las_points = crop_tile(config, raw_las_points)
                x_corner, y_corner = get_tile_origin_from_pointcloud(config, las_points)

                corner_string = f"{int(x_corner/1000)}_{int(y_corner/1000)}"
                # if intersect area == TILE_SIZE², this tile is fully inside the shapefile
                if intersect_area >= config.TILE_SIZE * config.TILE_SIZE or not to_be_cut:

                    df_result = update_df_result(df_result, df_key, corner_string, las_path)
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

                df_result = update_df_result(df_result, df_key, corner_string, cut_las_path)
                time_new = timeit.default_timer()
                delta_time = round(time_new - time_old, 2)
                logger.info(f"Processed {file_name} (cut) in {delta_time} sec")
                time_old = time_new

    time_end = timeit.default_timer()
    delta_time = round(time_end - time_start, 2)
    logger.info(f"Finished processing in {delta_time} sec")


if __name__ == "__main__":
    patchwork_dispatcher()
