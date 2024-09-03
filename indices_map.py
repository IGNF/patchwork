import numpy as np
from omegaconf import DictConfig
import rasterio as rs
from rasterio.transform import from_origin
from pandas import DataFrame

from tools import get_tile_origin_from_pointcloud


def create_indices_grid(config: DictConfig, df_points: DataFrame) -> np.ndarray:
    """ create a binary grid matching the tile, where each patch is equal to:
    1 if the patch has at least one new point
    0 if the patch has no new point
    """
    corner_x, corner_y = get_tile_origin_from_pointcloud(config, df_points)

    coordinate_x = np.int32((df_points.x - corner_x) / config.PATCH_SIZE)
    # coordinate_y is different from coordinate_x because of how rounding works
    # (corner_x is "bottom", corner_y is "top")
    coordinate_y = np.int32(corner_y / config.PATCH_SIZE) - np.int32(df_points.y / config.PATCH_SIZE) - 1
    grid = np.zeros((int(config.TILE_SIZE / config.PATCH_SIZE), int(config.TILE_SIZE / config.PATCH_SIZE)))

    grid[coordinate_x, coordinate_y] = 1
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
