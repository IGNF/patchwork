import sys

import numpy as np
import pandas as pd
from hydra import compose, initialize
import pytest

sys.path.append('../patchwork')

from tools import get_tile_origin_from_pointcloud

def test_get_tile_origin_from_pointcloud():

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"TILE_SIZE=1000",
            ]
        )

    # basic test
    list_x = [1100,1500]
    list_y = [2200,2800]
    points = np.core.records.fromarrays([list_x,list_y],names='x,y')

    corner_x, corner_y = get_tile_origin_from_pointcloud(config, points)
    assert corner_x == 1000
    assert corner_y == 3000

    # limit test 1
    list_x = [1000,2000]
    list_y = [1000,2000]
    points = np.core.records.fromarrays([list_x,list_y],names='x,y')

    corner_x, corner_y = get_tile_origin_from_pointcloud(config, points)
    assert corner_x == 1000
    assert corner_y == 2000

    # limit test 2
    list_x = [1500]
    list_y = [2300]
    points = np.core.records.fromarrays([list_x,list_y],names='x,y')

    corner_x, corner_y = get_tile_origin_from_pointcloud(config, points)
    assert corner_x == 1000
    assert corner_y == 3000

    # limit test 3
    list_x = []
    list_y = []
    points = np.core.records.fromarrays([list_x,list_y],names='x,y')

    with pytest.raises(ValueError):
        get_tile_origin_from_pointcloud(config, points)

    # failed test
    list_x = [1100,1500]
    list_y = [2200,3800]
    points = np.core.records.fromarrays([list_x,list_y],names='x,y')

    with pytest.raises(ValueError):
        get_tile_origin_from_pointcloud(config, points)