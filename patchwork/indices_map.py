import os

import numpy as np
import pandas as pd
import rasterio as rs
from omegaconf import DictConfig
from pandas import DataFrame
from rasterio.transform import from_origin

from patchwork.constants import PATCH_X_STR, PATCH_Y_STR


def create_indices_grid(config: DictConfig, df_points: DataFrame, corner_x: int, corner_y: int) -> np.ndarray:
    """create a binary grid matching the tile the points of df_points are from, where each patch is equal to:
    1 if the patch has at least one point of df_points
    0 if the patch has no point from df_points
    """
    size_grid = int(config.TILE_SIZE / config.PATCH_SIZE)

    grid = np.zeros((size_grid, size_grid))

    if not df_points.empty:
        list_coordinates_x = np.int32((df_points.x - corner_x) / config.PATCH_SIZE)
        list_coordinates_y = np.int32((corner_y - df_points.y) / config.PATCH_SIZE)

        # edge cases where points are exactly on the... edge of the tile, but still valid
        list_coordinates_x[list_coordinates_x == size_grid] = size_grid - 1
        list_coordinates_y[list_coordinates_y == size_grid] = size_grid - 1

        grid[list_coordinates_x, list_coordinates_y] = 1

    return grid.transpose()


def create_indices_map(config: DictConfig, df_points: DataFrame, corner_x: int, corner_y: int):
    """
    Save a binary grid for the tile into a geotiff
    """

    grid = create_indices_grid(config, df_points, corner_x, corner_y)
    os.makedirs(config.filepath.OUTPUT_INDICES_MAP_DIR, exist_ok=True)
    output_indices_map_path = os.path.join(
        config.filepath.OUTPUT_INDICES_MAP_DIR, config.filepath.OUTPUT_INDICES_MAP_NAME
    )

    transform = from_origin(corner_x, corner_y, config.PATCH_SIZE, config.PATCH_SIZE)
    indices_map = rs.open(
        output_indices_map_path,
        "w",
        driver="GTiff",
        height=grid.shape[0],
        width=grid.shape[1],
        count=1,
        dtype=str(grid.dtype),
        crs=config.CRS,
        transform=transform,
    )
    indices_map.write(grid, 1)
    indices_map.close()


def read_indices_map(config: DictConfig):
    indices_map = rs.open(os.path.join(config.filepath.INPUT_INDICES_MAP_DIR, config.filepath.INPUT_INDICES_MAP_NAME))
    transformer = indices_map.get_transform()
    grid = indices_map.read()
    grid = grid[0]
    grid_t = grid.transpose()
    list_coordinates = np.argwhere(grid_t == 1)

    list_coordinates = list_coordinates.transpose()

    patch_x = list_coordinates[0] * config.PATCH_SIZE + transformer[0]
    patch_y = grid.shape[1] - (transformer[3] - list_coordinates[1] * config.PATCH_SIZE)

    table = np.array([patch_x, patch_y]).transpose()
    field = [PATCH_X_STR, PATCH_Y_STR]

    df_indices = pd.DataFrame(table, columns=field)
    return df_indices
