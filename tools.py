import numpy as np
from typing import Tuple

from laspy import ScaleAwarePointRecord
import laspy

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

def identify_bounds(config: DictConfig, points: ScaleAwarePointRecord) -> Tuple[int, int,int, int]:
    """Return the bounds of a tile represented by its points"""
    gravity_x = np.sum(points['x']) / len(points)
    gravity_y = np.sum(points['y']) / len(points)
    min_x =  int(gravity_x / config.TILE_SIZE) * config.TILE_SIZE
    max_x =  int(gravity_x / config.TILE_SIZE) * config.TILE_SIZE + config.TILE_SIZE
    min_y =  int(gravity_y / config.TILE_SIZE) * config.TILE_SIZE
    max_y =  int(gravity_y / config.TILE_SIZE) * config.TILE_SIZE + config.TILE_SIZE

    return min_x, max_x, min_y, max_y


def crop_tile(config: DictConfig, points: ScaleAwarePointRecord)-> np.ndarray:
    """Crop points to the tile containing the center of gravity"""
    min_x, max_x, min_y, max_y = identify_bounds(config, points)
    return points[(points['x']>= min_x) & (points['x']<= max_x) & (points['y']>= min_y) & (points['y']<= max_y)]

MIN_X, MAX_X, MIN_Y, MAX_Y = 881670, 881671, 6440887, 6440888
DONOR_FILE = "/home/MDaab/data/mix/Echantillon_Chantier_Drome_Ardeche_C_Bloc_OM/LiDAR_BD/0881_6441.laz"
RECIPIENT_FILE = "/home/MDaab/data/mix/Echantillon_Chantier_Drome_Ardeche_C_Bloc_OM/LiDAR_HD/Semis_2021_0881_6441_LA93_IGN69.laz"

def crop_temp():
    min_x, max_x, min_y, max_y = MIN_X, MAX_X, MIN_Y, MAX_Y
    with laspy.open(DONOR_FILE) as donor_file, \
            laspy.open(RECIPIENT_FILE) as recipient_file:
        raw_donor_points = donor_file.read().points
        donor_points = raw_donor_points[(raw_donor_points['x']>= min_x) & (raw_donor_points['x']< max_x) & (raw_donor_points['y']>= min_y) & (raw_donor_points['y']< max_y)]
        raw_recipient_points = recipient_file.read().points
        recipient_points = raw_recipient_points[(raw_recipient_points['x']>= min_x) & (raw_recipient_points['x']< max_x) & (raw_recipient_points['y']>= min_y) & (raw_recipient_points['y']< max_y)]
        donor_class = np.unique(donor_points['classification'])
        recipient_class = np.unique(recipient_points['classification'])
        pass