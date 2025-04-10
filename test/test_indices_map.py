import os

import numpy as np
import pandas as pd
import rasterio as rs
from hydra import compose, initialize
from rasterio.transform import from_origin

from patchwork.constants import PATCH_X_STR, PATCH_Y_STR
from patchwork.indices_map import (
    create_indices_grid,
    create_indices_map,
    read_indices_map,
)

PATCH_SIZE = 1
TILE_SIZE = 3

DATA_POINTS = {"x": [0.0, 1.5, 3, 1.5, 2.5], "y": [0.0, 0.5, 0.5, 1.5, 3]}
# we want y=0 at the bottom, but in a ndarray it's at the top, so grid['y'] = SIZE_Y - data_points['y']
POINTS_IN_GRID = [(0, 2), (1, 2), (2, 2), (1, 1), (2, 0)]
POINTS_NOT_IN_GRID = [(0, 1), (2, 1), (0, 0), (0, 1)]


def test_create_indices_points():
    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml", overrides=[f"PATCH_SIZE={PATCH_SIZE}", f"TILE_SIZE={TILE_SIZE}"]
        )
        df_points = pd.DataFrame(data=DATA_POINTS)
        grid = create_indices_grid(config, df_points)

        grid = grid.transpose()  # indices aren't read the way we want otherwise

        for point in POINTS_IN_GRID:
            assert grid[point] == 1
        for point in POINTS_NOT_IN_GRID:
            assert grid[point] == 0


def test_create_indices_map(tmp_path_factory):
    tmp_file_dir = tmp_path_factory.mktemp("data")
    tmp_file_name = "indices.tif"

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"PATCH_SIZE={PATCH_SIZE}",
                f"TILE_SIZE={TILE_SIZE}",
                f"filepath.OUTPUT_INDICES_MAP_DIR={tmp_file_dir}",
                f"filepath.OUTPUT_INDICES_MAP_NAME={tmp_file_name}",
            ],
        )

        df_points = pd.DataFrame(data=DATA_POINTS)
        create_indices_map(config, df_points)
        raster = rs.open(os.path.join(tmp_file_dir, tmp_file_name))
        grid = raster.read()

        grid = grid.transpose()  # indices aren't read the way we want otherwise

        for point in POINTS_IN_GRID:
            assert grid[point] == 1
        for point in POINTS_NOT_IN_GRID:
            assert grid[point] == 0


def test_read_indices_map(tmp_path_factory):
    tmp_file_dir = tmp_path_factory.mktemp("data")
    tmp_file_name = "indices.tif"

    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"PATCH_SIZE={PATCH_SIZE}",
                f"TILE_SIZE={TILE_SIZE}",
                f"filepath.INPUT_INDICES_MAP_DIR={tmp_file_dir}",
                f"filepath.INPUT_INDICES_MAP_NAME={tmp_file_name}",
            ],
        )

        grid = np.array(
            [
                [0, 0, 1],
                [0, 1, 0],
                [1, 1, 1],
            ]
        )

        transform = from_origin(0, 3, config.PATCH_SIZE, config.PATCH_SIZE)
        output_indices_map_path = os.path.join(
            config.filepath.INPUT_INDICES_MAP_DIR, config.filepath.INPUT_INDICES_MAP_NAME
        )
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

        df_indices = read_indices_map(config)
        for _, row in df_indices.iterrows():
            assert (row[PATCH_X_STR], row[PATCH_Y_STR]) in POINTS_IN_GRID
        assert len(df_indices) == len(POINTS_IN_GRID)
