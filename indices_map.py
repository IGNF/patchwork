import numpy as np
from omegaconf import DictConfig
import rasterio as rs
from rasterio.transform import from_origin
import pandas as pd
from pandas import DataFrame

from tools import get_tile_origin_from_pointcloud
from constants import PATCH_X_STR, PATCH_Y_STR

def create_indices_grid(config: DictConfig, df_points: DataFrame) -> np.ndarray:
    """ create a binary grid matching the tile the points of df_points are from, where each patch is equal to:
    1 if the patch has at least one point of df_points
    0 if the patch has no point from df_points
    """
    size_grid = int(config.TILE_SIZE / config.PATCH_SIZE)

    corner_x, corner_y = get_tile_origin_from_pointcloud(config, df_points)

    list_coordinates_x = np.int32((df_points.x - corner_x) / config.PATCH_SIZE)
    list_coordinates_y = np.int32((corner_y - df_points.y) / config.PATCH_SIZE)

    # edge cases where points are exactly on the... edge of the tile, but still valid 
    list_coordinates_x[list_coordinates_x == size_grid] = size_grid - 1
    list_coordinates_y[list_coordinates_y == size_grid] = size_grid - 1

    grid = np.zeros((size_grid, size_grid))

    grid[list_coordinates_x, list_coordinates_y] = 1
    return grid.transpose()


def create_indices_map(config: DictConfig, df_points: DataFrame):
    """
    Save a binary grid for the tile into a geotiff
    """
    corner_x, corner_y = get_tile_origin_from_pointcloud(config, df_points)

    grid = create_indices_grid(config, df_points)

    transform = from_origin(corner_x, corner_y, config.PATCH_SIZE, config.PATCH_SIZE)
    indices_map = rs.open(config.filepath.OUTPUT_INDICES_MAP, 'w', driver='GTiff',
                          height=grid.shape[0], width=grid.shape[1],
                          count=1, dtype=str(grid.dtype),
                          crs=config.CRS,
                          transform=transform)
    indices_map.write(grid, 1)
    indices_map.close()

def read_indices_map(config: DictConfig):
    indices_map = rs.open(config.filepath.INPUT_INDICES_MAP)
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
