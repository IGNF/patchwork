import os
from shutil import copy2
from typing import List, Tuple

import geopandas as gpd
import laspy
import numpy as np
import pandas as pd
from laspy import LasReader, ScaleAwarePointRecord
from omegaconf import DictConfig
from pdaltools.las_info import get_tile_origin_using_header_info

import patchwork.constants as c
from patchwork.indices_map import create_indices_map
from patchwork.shapefile_data_extraction import get_donor_info_from_shapefile


def get_selected_classes_points(
    tile_origin: Tuple[int, int],
    points_list: ScaleAwarePointRecord,
    class_list: list[int],
    use_synthetic_points: bool,
    fields_to_keep: list[str],
    patch_size: int,
    tile_size: int,
) -> pd.DataFrame:
    """Get a list of points from a las, filter them based on classification an d synthetic flag
    and return them as a pandas dataframe

    Args:
        tile_origin (Tuple[int, int]): Origin point of the tile (in meters)
        points_list (ScaleAwarePointRecord): Points list in laspy format
        class_list (list[int]): List of classes to keep
        use_synthetic_points (bool): if false, filter out points with flag "synthetic" = True
        fields_to_keep (list[str]): Las file attribute to keep in the output dataframe
        patch_size (int): Size of the patches (for discretization)
        tile_size (int): Size of the tile

    Raises:
        NotImplementedError: Filtering out synthetic points is implemented only
        if the synthetic field is in fields_to_keep

    Returns:
        pd.DataFrame: Filtered points list as a pd.DataFrame
    """
    # we add automatically classification, so we remove it if it's in field_to_keep
    if c.CLASSIFICATION_STR in fields_to_keep:
        fields_to_keep.remove(c.CLASSIFICATION_STR)

    table_fields_to_keep = [points_list[field] for field in fields_to_keep]
    table_field_necessary = [
        np.int32(points_list.x / patch_size),  # convert x into the coordinate of the patch
        np.int32(points_list.y / patch_size),  # convert y into the coordinate of the patch
        points_list.classification,
    ]
    all_fields_list = [*fields_to_keep, c.PATCH_X_STR, c.PATCH_Y_STR, c.CLASSIFICATION_STR]

    all_classes_points = np.array(table_fields_to_keep + table_field_necessary).transpose()
    df_points = pd.DataFrame(all_classes_points, columns=all_fields_list)

    # Filter points based on classification
    df_points = df_points[df_points.classification.isin(class_list)]

    # Filter based on if the point is synthetic
    if not use_synthetic_points:
        if "synthetic" in fields_to_keep:
            df_points = df_points[np.logical_not(df_points.synthetic)]
        else:
            raise NotImplementedError(
                "'get_selected_classes_points' is asked to filter on synthetic flag, "
                "but this flag is not in fields to keep."
            )

    # "push" the points on the limit of the tile to the closest patch
    mask_points_on_max_x = df_points[c.PATCH_X_STR] == tile_origin[0] + tile_size
    df_points.loc[mask_points_on_max_x, c.PATCH_X_STR] = tile_origin[0] + tile_size - 1
    mask_points_on_max_y = df_points[c.PATCH_Y_STR] == tile_origin[1]
    df_points.loc[mask_points_on_max_y, c.PATCH_Y_STR] = tile_origin[1] - 1

    return df_points


def get_type(new_column_size: int):
    """return the type matching the new_column_size (must be in [8,16,32,64])"""
    match new_column_size:
        case 8:
            return np.int8
        case 16:
            return np.int16
        case 32:
            return np.int32
        case 64:
            return np.int64
        case _:
            raise ValueError(f"{new_column_size} is not a correct value for NEW_COLUMN_SIZE")


def get_complementary_points(
    df_donor_info: gpd.GeoDataFrame, recipient_file_path: str, tile_origin: Tuple[int, int], config: DictConfig
) -> pd.DataFrame:
    with laspy.open(recipient_file_path) as recipient_file:
        recipient_points = recipient_file.read().points

    df_recipient_points = get_selected_classes_points(
        tile_origin,
        recipient_points,
        config.RECIPIENT_CLASS_LIST,
        use_synthetic_points=True,
        fields_to_keep=[],
        patch_size=config.PATCH_SIZE,
        tile_size=config.TILE_SIZE,
    )

    # set, for each patch of coordinate (patch_x, patch_y), the number of recipient point
    # should have no record for when count == 0, therefore "df_recipient_non_empty_patches" list all
    # and only the patches with at least a point
    # In other words, the next column should be filled with "False" everywhere
    df_recipient_non_empty_patches = (
        df_recipient_points.groupby(by=[c.PATCH_X_STR, c.PATCH_Y_STR]).count().classification == 0
    )

    dfs_donor_points = []

    for index, row in df_donor_info.iterrows():
        with laspy.open(row["full_path"]) as donor_file:
            raw_donor_points = donor_file.read().points
            points_loc_gdf = gpd.GeoDataFrame(
                geometry=gpd.points_from_xy(raw_donor_points.x, raw_donor_points.y, raw_donor_points.z, crs=config.CRS)
            )
            footprint_gdf = gpd.GeoDataFrame(geometry=[row["geometry"]], crs=config.CRS)
            points_in_footprint_gdf = points_loc_gdf.sjoin(footprint_gdf, how="inner", predicate="intersects")
            donor_points = raw_donor_points[points_in_footprint_gdf.index.values]

            donor_columns = get_field_from_header(donor_file)
            dfs_donor_points.append(
                get_selected_classes_points(
                    tile_origin,
                    donor_points,
                    config.DONOR_CLASS_LIST,
                    config.DONOR_USE_SYNTHETIC_POINTS,
                    donor_columns,
                    patch_size=config.PATCH_SIZE,
                    tile_size=config.TILE_SIZE,
                )
            )

    if len(df_donor_info.index):
        df_donor_points = pd.concat(dfs_donor_points)

    else:
        df_donor_points = gpd.GeoDataFrame(columns=["x", "y", "z", "patch_x", "patch_y", "classification"])

    # for each (patch_x,patch_y) patch, we join to a donor point the count of recipient points on that patch
    # since it's a left join, it keeps all the left record (all the donor points)
    #  and put a "NaN" if the recipient point count is null (no record)
    joined_patches = pd.merge(
        df_donor_points,
        df_recipient_non_empty_patches,
        on=[c.PATCH_X_STR, c.PATCH_Y_STR],
        how="left",
        suffixes=("", c.RECIPIENT_SUFFIX),
    )

    # only keep donor points in patches where there is no recipient point
    return joined_patches.loc[joined_patches[c.CLASSIFICATION_STR + c.RECIPIENT_SUFFIX].isnull()]


def get_field_from_header(las_file: LasReader) -> List[str]:
    """From an opened las, get all the column names in lower case
    Lower case so a comparaison between fields from 2 different files won't fail because of the case"""
    header = las_file.header
    return [dimension.name.lower() for dimension in header.point_format.dimensions]


def test_field_exists(file_path: str, column: str) -> bool:
    output_file = laspy.read(file_path)
    return column in get_field_from_header(output_file)


def append_points(config: DictConfig, extra_points: pd.DataFrame):
    # get field to copy :
    recipient_filepath = os.path.join(config.filepath.RECIPIENT_DIRECTORY, config.filepath.RECIPIENT_NAME)
    output_filepath = os.path.join(config.filepath.OUTPUT_DIR, config.filepath.OUTPUT_NAME)
    with laspy.open(recipient_filepath) as recipient_file:
        recipient_fields_list = get_field_from_header(recipient_file)

    # get fields that are in the donor file we can transmit to the recipient without problem
    # classification is in the fields to exclude because it will be copied in a special way
    fields_to_exclude = [
        c.PATCH_X_STR,
        c.PATCH_Y_STR,
        c.CLASSIFICATION_STR,
        c.CLASSIFICATION_STR + c.RECIPIENT_SUFFIX,
    ]

    fields_to_keep = [
        field
        for field in recipient_fields_list
        if (field.lower() in extra_points.columns) and (field.lower() not in fields_to_exclude)
    ]

    copy2(recipient_filepath, output_filepath)

    # if we want a new column, we start by adding its name
    if config.NEW_COLUMN:
        if test_field_exists(recipient_filepath, config.NEW_COLUMN):
            raise ValueError(
                f"{config.NEW_COLUMN} already exists as \
                             column name in {recipient_filepath}"
            )
        new_column_type = get_type(config.NEW_COLUMN_SIZE)
        output_las = laspy.read(output_filepath)
        output_las.add_extra_dim(
            laspy.ExtraBytesParams(
                name=config.NEW_COLUMN,
                type=new_column_type,
                description="Point origin: 0=initial las",
            )
        )
        output_las.write(output_filepath)

    if len(extra_points) == 0:  # if no point to add, the job is done after copying the recipient file
        return

    with laspy.open(output_filepath, mode="a") as output_las:
        # put in a new table all extra points and their values on the fields we want to keep
        new_points = laspy.ScaleAwarePointRecord.zeros(extra_points.shape[0], header=output_las.header)
        for field in fields_to_keep:
            new_points[field] = extra_points[field].astype(new_points[field])

        if not config.NEW_COLUMN:
            # translate the classification values:
            for classification in config.DONOR_CLASS_LIST:
                new_classification = config.VIRTUAL_CLASS_TRANSLATION[classification]
                extra_points.loc[extra_points[c.CLASSIFICATION_STR] == classification, c.CLASSIFICATION_STR] = (
                    new_classification
                )

        else:
            extra_points[config.NEW_COLUMN] = config.VALUE_ADDED_POINTS
            new_points[config.NEW_COLUMN] = extra_points[config.NEW_COLUMN]

        new_points.classification = extra_points[c.CLASSIFICATION_STR]
        output_las.append_points(new_points)


def patchwork(config: DictConfig):
    recipient_filepath = os.path.join(config.filepath.RECIPIENT_DIRECTORY, config.filepath.RECIPIENT_NAME)
    origin_x_meters, origin_y_meters = get_tile_origin_using_header_info(recipient_filepath, config.TILE_SIZE)
    x_shapefile = origin_x_meters / config.SHP_X_Y_TO_METER_FACTOR
    y_shapefile = origin_y_meters / config.SHP_X_Y_TO_METER_FACTOR

    shapefile_path = os.path.join(config.filepath.SHP_DIRECTORY, config.filepath.SHP_NAME)
    donor_info_df = get_donor_info_from_shapefile(
        shapefile_path, x_shapefile, y_shapefile, config.filepath.DONOR_SUBDIRECTORY, config.mount_points
    )

    complementary_bd_points = get_complementary_points(
        donor_info_df, recipient_filepath, (origin_x_meters, origin_y_meters), config
    )

    append_points(config, complementary_bd_points)

    corner_x, corner_y = get_tile_origin_using_header_info(filename=recipient_filepath, tile_width=config.TILE_SIZE)
    create_indices_map(config, complementary_bd_points, corner_x, corner_y)
