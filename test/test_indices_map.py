import sys

from hydra import compose, initialize
import pandas as pd
import rasterio as rs

sys.path.append('../patchwork')

from indices_map import create_indices_grid, create_indices_map

PATCH_SIZE = 1
TILE_SIZE = 3

DATA_POINTS = {'x': [0.0, 1.5, 2.5, 1.5, 2.5], 'y': [0.0, 0.5, 0.5, 1.5, 2.5]}
# we want y=0 at the bottom, but in a ndarray it's at the top, so grid['y'] = SIZE_Y - data_points['y']
POINTS_IN_GRID = [(0, 2), (1, 2), (2, 2), (1, 1), (2, 0)]
POINTS_NOT_IN_GRID = [(0, 1), (2, 1), (0, 0), (0, 1)]


def test_create_indices_points():
    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"PATCH_SIZE={PATCH_SIZE}",
                f"TILE_SIZE={TILE_SIZE}"
            ]
        )
        df_points = pd.DataFrame(data=DATA_POINTS)
        grid = create_indices_grid(config, df_points)

        grid = grid.transpose()  # indices aren't read the way we want otherwise

        for point in POINTS_IN_GRID:
            assert grid[point] == 1
        for point in POINTS_NOT_IN_GRID:
            assert grid[point] == 0


def test_create_indices_map(tmp_path_factory):
    tmp_file_path = tmp_path_factory.mktemp("data") / "indices.tif"
    with initialize(version_base="1.2", config_path="../configs"):
        config = compose(
            config_name="configs_patchwork.yaml",
            overrides=[
                f"PATCH_SIZE={PATCH_SIZE}",
                f"TILE_SIZE={TILE_SIZE}",
                f"filepath.OUTPUT_INDICES_MAP={tmp_file_path}",
            ]
        )

        df_points = pd.DataFrame(data=DATA_POINTS)
        create_indices_map(config, df_points)
        raster = rs.open(tmp_file_path)
        grid = raster.read()

        grid = grid.transpose()  # indices aren't read the way we want otherwise

        for point in POINTS_IN_GRID:
            assert grid[point] == 1
        for point in POINTS_NOT_IN_GRID:
            assert grid[point] == 0
