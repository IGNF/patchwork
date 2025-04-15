import os
from pathlib import Path
from shutil import copy2
from typing import List, Tuple

import laspy
import numpy as np
import pandas as pd
from laspy import LasReader, ScaleAwarePointRecord
from omegaconf import DictConfig

import patchwork.constants as c
from patchwork.indices_map import create_indices_map
from patchwork.tools import crop_tile, get_tile_origin_from_pointcloud


def get_selected_classes_points(
    config: DictConfig,
    tile_origin: Tuple[int, int],
    points_list: ScaleAwarePointRecord,
    class_list: list[int],
    fields_to_keep: list[str],
) -> pd.DataFrame:
    """get a list of points from a las, and return a ndarray of those point with the selected classification"""

    # we add automatically classification, so we remove it if it's in field_to_keep
    if c.CLASSIFICATION_STR in fields_to_keep:
        fields_to_keep.remove(c.CLASSIFICATION_STR)

    table_fields_to_keep = [points_list[field] for field in fields_to_keep]
    table_field_necessary = [
        np.int32(points_list.x / config.PATCH_SIZE),  # convert x into the coordinate of the patch
        np.int32(points_list.y / config.PATCH_SIZE),  # convert y into the coordinate of the patch
        points_list.classification,
    ]

    all_classes_points = np.array(table_fields_to_keep + table_field_necessary).transpose()

    mask = np.zeros(len(all_classes_points), dtype=bool)
    for classification in class_list:
        mask = mask | (all_classes_points[:, -1] == classification)
    wanted_classes_points = all_classes_points[mask]
    all_fields_list = [*fields_to_keep, c.PATCH_X_STR, c.PATCH_Y_STR, c.CLASSIFICATION_STR]
    df_wanted_classes_points = pd.DataFrame(wanted_classes_points, columns=all_fields_list)

    # "push" the points on the limit of the tile to the closest patch
    mask_points_on_max_x = df_wanted_classes_points[c.PATCH_X_STR] == tile_origin[0] + config.TILE_SIZE
    df_wanted_classes_points.loc[mask_points_on_max_x, c.PATCH_X_STR] = tile_origin[0] + config.TILE_SIZE - 1
    mask_points_on_max_y = df_wanted_classes_points[c.PATCH_Y_STR] == tile_origin[1]
    df_wanted_classes_points.loc[mask_points_on_max_y, c.PATCH_Y_STR] = tile_origin[1] - 1

    return df_wanted_classes_points


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


def get_complementary_points(config: DictConfig) -> pd.DataFrame:
    donor_dir, donor_name = get_donor_path(config)
    donor_file_path = os.path.join(donor_dir, donor_name)
    recipient_file_path = os.path.join(config.filepath.RECIPIENT_DIRECTORY, config.filepath.RECIPIENT_NAME)

    with laspy.open(donor_file_path) as donor_file, laspy.open(recipient_file_path) as recipient_file:
        raw_donor_points = donor_file.read().points
        donor_points = crop_tile(config, raw_donor_points)
        raw_recipient_points = recipient_file.read().points
        recipient_points = crop_tile(config, raw_recipient_points)

        # check if both files are on the same area
        tile_origin_donor = get_tile_origin_from_pointcloud(config, donor_points)
        tile_origin_recipient = get_tile_origin_from_pointcloud(config, recipient_points)
        if tile_origin_donor != tile_origin_recipient:
            raise ValueError(
                f"{donor_file_path} and \
                             {recipient_file_path} are not on the same area"
            )

        donor_columns = get_field_from_header(donor_file)
        df_donor_points = get_selected_classes_points(
            config, tile_origin_donor, donor_points, config.DONOR_CLASS_LIST, donor_columns
        )
        df_recipient_points = get_selected_classes_points(
            config, tile_origin_recipient, recipient_points, config.RECIPIENT_CLASS_LIST, []
        )

        # set, for each patch of coordinate (patch_x, patch_y), the number of recipient point
        # should have no record for when count == 0, therefore "df_recipient_non_empty_patches" list all
        # and only the patches with at least a point
        # In other words, the next column should be filled with "False" everywhere
        df_recipient_non_empty_patches = (
            df_recipient_points.groupby(by=[c.PATCH_X_STR, c.PATCH_Y_STR]).count().classification == 0
        )

        # for each (patch_x,patch_y) patch, we join to a donor point the count of recipient points on that patch
        # since it's a left join, it keeps all the left record (all the donor points)
        #  and put a "NaN" if the recipient point count is null (no record)
        joined_patches = pd.merge(
            df_donor_points,
            df_recipient_non_empty_patches,
            on=[c.PATCH_X_STR, c.PATCH_Y_STR],
            how="left",
            suffixes=("", config.RECIPIENT_SUFFIX),
        )

        # only keep donor points in patches where there is no recipient point
        return joined_patches.loc[joined_patches[c.CLASSIFICATION_STR + config.RECIPIENT_SUFFIX].isnull()]


def get_field_from_header(las_file: LasReader) -> List[str]:
    """From an opened las, get all the column names in lower case
    Lower case so a comparaison between fields from 2 different files won't fail because of the case"""
    header = las_file.header
    return [dimension.name.lower() for dimension in header.point_format.dimensions]


def test_field_exists(file_path: str, colmun: str) -> bool:
    output_file = laspy.read(file_path)
    return colmun in get_field_from_header(output_file)


def append_points(config: DictConfig, extra_points: pd.DataFrame):
    # get field to copy :
    recipient_filepath = os.path.join(config.filepath.RECIPIENT_DIRECTORY, config.filepath.RECIPIENT_NAME)
    ouput_filepath = os.path.join(config.filepath.OUTPUT_DIR, config.filepath.OUTPUT_NAME)
    with laspy.open(recipient_filepath) as recipient_file:
        recipient_fields_list = get_field_from_header(recipient_file)

    # get fields that are in the donor file we can transmit to the recipient without problem
    # classification is in the fields to exclude because it will be copy in a special way
    fields_to_exclude = [
        c.PATCH_X_STR,
        c.PATCH_Y_STR,
        c.CLASSIFICATION_STR,
        c.CLASSIFICATION_STR + config.RECIPIENT_SUFFIX,
    ]

    fields_to_keep = [
        field
        for field in recipient_fields_list
        if (field.lower() in extra_points.columns) and (field.lower() not in fields_to_exclude)
    ]

    copy2(recipient_filepath, ouput_filepath)

    if len(extra_points) == 0:  # if no point to add, the job is done after copying the recipient file
        return

    # if we want a new column, we start by adding its name
    if config.NEW_COLUMN:
        if test_field_exists(recipient_filepath, config.NEW_COLUMN):
            raise ValueError(
                f"{config.NEW_COLUMN} already exists as \
                             column name in {recipient_filepath}"
            )
        new_column_type = get_type(config.NEW_COLUMN_SIZE)
        output_las = laspy.read(ouput_filepath)
        output_las.add_extra_dim(laspy.ExtraBytesParams(name=config.NEW_COLUMN, type=new_column_type))
        output_las.write(ouput_filepath)

    with laspy.open(ouput_filepath, mode="a") as output_las:
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


def get_donor_from_csv(recipient_file_path: str, csv_file_path: str) -> str:
    """
    check if there is a donor file, in the csv file, matching the recipient file
    return the path to that file if it exists
    return "" otherwise
    """
    df_csv_data = pd.read_csv(csv_file_path)
    donor_file_paths = df_csv_data.loc[df_csv_data[c.RECIPIENT_FILE_KEY] == recipient_file_path, c.DONOR_FILE_KEY]
    if len(donor_file_paths) == 1:
        return donor_file_paths.iloc[0]
    elif len(donor_file_paths) == 0:
        return ""
    else:
        raise RuntimeError(
            f"Found more than one donor file associated with recipient file {recipient_file_path}."
            "Please check the matching csv file"
        )


def get_donor_path(config: DictConfig) -> Tuple[str, str]:
    """Return a donor directory and a name:
    If there is no csv file provided in config, return  DONOR_DIRECTORY and DONOR_NAME
    if there is a csv file provided, return DONOR_DIRECTORY and DONOR_NAME matching the given RECIPIENT
    if there is a csv file provided but no matching DONOR, return "" twice"""
    if config.filepath.CSV_DIRECTORY and config.filepath.CSV_NAME:
        csv_file_path = os.path.join(config.filepath.CSV_DIRECTORY, config.filepath.CSV_NAME)
        recipient_file_path = os.path.join(config.filepath.RECIPIENT_DIRECTORY, config.filepath.RECIPIENT_NAME)
        donor_file_path = get_donor_from_csv(recipient_file_path, csv_file_path)
        if not donor_file_path:  # if there is no matching donor file, we do nothing
            return "", ""
        return str(Path(donor_file_path).parent), str(Path(donor_file_path).name)
    return config.filepath.DONOR_DIRECTORY, config.filepath.DONOR_NAME


def patchwork(config: DictConfig):
    _, donor_name = get_donor_path(config)
    if not donor_name:  # if no matching donor, we simply copy the recipient to the output without doing anything
        recipient_filepath = os.path.join(config.filepath.RECIPIENT_DIRECTORY, config.filepath.RECIPIENT_NAME)
        ouput_filepath = os.path.join(config.filepath.OUTPUT_DIR, config.filepath.OUTPUT_NAME)
        copy2(recipient_filepath, ouput_filepath)
        return

    complementary_bd_points = get_complementary_points(config)
    append_points(config, complementary_bd_points)
    create_indices_map(config, complementary_bd_points)
