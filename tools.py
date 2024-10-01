import numpy as np
from typing import Tuple

from laspy import ScaleAwarePointRecord

from omegaconf import DictConfig


def get_tile_origin_from_pointcloud(config: DictConfig, points: np.ndarray | ScaleAwarePointRecord) -> Tuple[int, int]:
    """Return the coordinate of the upper left corner of an area defined by the points it contains"""
    if not len(points):
        raise ValueError("No points to determine the coordinate of the tile")

    x_min = np.min(points['x'], axis=0)
    x_max = np.max(points['x'], axis=0)
    y_min = np.min(points['y'], axis=0)
    y_max = np.max(points['y'], axis=0)

    length_tile_x = x_max / config.TILE_SIZE - np.floor(x_min / config.TILE_SIZE)
    length_tile_y = np.ceil(y_max / config.TILE_SIZE) - y_min / config.TILE_SIZE

    if (length_tile_x <= 1) and (length_tile_y <= 1):
        origin_x = np.floor(x_min / config.TILE_SIZE) * config.TILE_SIZE
        origin_y = np.ceil(y_max / config.TILE_SIZE) * config.TILE_SIZE
        return origin_x, origin_y
    else:
        raise ValueError(
            f"Min values (x={x_min} and y={y_min}) do not belong to the same theoretical tile as"
            f"max values (x={x_max} and y={y_max})."
        )


def identify_bounds(tile_size: float, points: ScaleAwarePointRecord) -> Tuple[int, int, int, int]:
    """Return the bounds of a tile represented by its points"""
    gravity_x = np.sum(points['x']) / len(points)
    gravity_y = np.sum(points['y']) / len(points)
    min_x = int(gravity_x / tile_size) * tile_size
    max_x = int(gravity_x / tile_size) * tile_size + tile_size
    min_y = int(gravity_y / tile_size) * tile_size
    max_y = int(gravity_y / tile_size) * tile_size + tile_size

    return min_x, max_x, min_y, max_y


def crop_tile(config: DictConfig, points: ScaleAwarePointRecord) -> np.ndarray:
    """Crop points to the tile containing the center of gravity"""
    min_x, max_x, min_y, max_y = identify_bounds(config.TILE_SIZE, points)
    return points[(points['x'] >= min_x) & (points['x'] <= max_x) & (points['y'] >= min_y) & (points['y'] <= max_y)]
