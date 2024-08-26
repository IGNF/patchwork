
from shutil import copy2
from typing import List

from omegaconf import DictConfig

import numpy as np
import pandas as pd
import laspy
from laspy import ScaleAwarePointRecord, LasReader


def get_selected_classes_points(config: DictConfig,
                                points_list: ScaleAwarePointRecord,
                                class_list: list[int],
                                fields_to_keep: list[str]) -> pd.DataFrame:
    """get a list of points from a las, and return a ndarray of those point with the selected classification
    """

    # we add automatically classification, so we remove it if it's in field_to_keep
    if "classification" in fields_to_keep:
        fields_to_keep.remove("classification")

    table_fields_to_keep = [points_list[field] for field in fields_to_keep]
    table_field_necessary = [
        np.int32(points_list.x / config.PATCH_SIZE),  # convert x into the coordinate of the patch
        np.int32(points_list.y / config.PATCH_SIZE),  # convert y into the coordinate of the patch
        points_list.classification
        ]

    all_classes_points = np.array(table_fields_to_keep + table_field_necessary).transpose()

    mask = np.zeros(len(all_classes_points), dtype=bool)
    for classification in class_list:
        mask = mask | (all_classes_points[:, -1] == classification)
    wanted_classes_points = all_classes_points[mask]
    all_fields_list = [*fields_to_keep, 'patch_x', 'patch_y', 'classification']
    df_wanted_classes_points = pd.DataFrame(wanted_classes_points, columns=all_fields_list)

    return df_wanted_classes_points


# def is_column_exist(laspath: str, new_column_name) -> bool:
#     with laspy.open(laspath) as las_file:
#         if new_column_name in las_file.sub_fields_dict.keys():
#             return True
#     return False


def get_type(new_column_size: int):
    """ return the type matching the new_column_size (must be in [8,16,32,64])"""
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
    with laspy.open(config.filepath.DONOR_FILE) as donor_file, \
            laspy.open(config.filepath.RECIPIENT_FILE) as recipient_file:
        donor_points = donor_file.read().points
        recipient_points = recipient_file.read().points

        donor_columns = get_field_from_header(donor_file)
        df_donor_points = get_selected_classes_points(config, donor_points, config.DONOR_CLASS_LIST, donor_columns)
        df_recipient_points = get_selected_classes_points(config, recipient_points, config.RECIPIENT_CLASS_LIST, [])

        # set, for each patch of coordinate (patch_x, patch_y), the number of recipient point
        # should have no record for when count == 0, therefore "df_recipient_non_empty_patches" list all
        # and only the patches with at least a point
        # In other words, the next column should be filled with "False" everywhere
        df_recipient_non_empty_patches = df_recipient_points.groupby(by=['patch_x', 'patch_y']).count().classification == 0

        # for each (patch_x,patch_y) patch, we join to a donor point the count of recipient points on that patch
        # since it's a left join, it keeps all the left record (all the donor points)
        #  and put a "NaN" if the recipient point count is null (no record)
        joined_patches = pd.merge(df_donor_points,
                                  df_recipient_non_empty_patches,
                                  on=['patch_x', 'patch_y'],
                                  how='left',
                                  suffixes=('', config.RECIPIENT_SUFFIX)
                                  )

        # only keep donor points in patches where there is no recipient point
        extra_points = joined_patches.loc[joined_patches["classification" + config.RECIPIENT_SUFFIX].isnull()]
        return extra_points


def get_field_from_header(las_file: LasReader) -> List[str]:
    """From an opened las, get all the column names in lower case
    Lower case so a comparaison between fields from 2 diffrent files won't fail because of the case"""
    header = las_file.header
    return [dimension.name.lower() for dimension in header.point_format.dimensions]


def append_points(config: DictConfig, extra_points: pd.DataFrame):
    # get field to copy :
    recipient_filepath = config.filepath.RECIPIENT_FILE
    ouput_filepath = config.filepath.OUTPUT_FILE
    with laspy.open(recipient_filepath) as recipient_file:
        recipient_fields_list = get_field_from_header(recipient_file)

    # get fields that are in the donor file we can transmit to the recipient whitout problem
    # classification is in the fields to exclude because it will be copy in a special way
    fields_to_exclude = ["patch_x", "patch_y", "classification", "classification" + config.RECIPIENT_SUFFIX]

    fields_to_keep = [field for field in recipient_fields_list if
                      (field.lower() in extra_points.columns)
                      and (field.lower() not in fields_to_exclude)
                      ]

    copy2(recipient_filepath, ouput_filepath)

    with laspy.open(ouput_filepath, mode="a") as output_las:
        # # if we want a new column, we start by adding its name
        # if NEW_COLUMN:
        #     test_column_exists(ouput_file, NEW_COLUMN)
        #     new_column_type = get_type(NEW_COLUMN_SIZE)
        #     output_las.add_extra_dim(laspy.ExtraBytesParams(name=NEW_COLUMN, type=new_column_type))

        # put in a new table all extra points and their values on the fields we want to keep
        new_points = laspy.ScaleAwarePointRecord.zeros(extra_points.shape[0], header=output_las.header)
        for field in fields_to_keep:
            new_points[field] = extra_points[field].astype(new_points[field])

        if not config.NEW_COLUMN:
            # translate the classification values:
            for classification in config.DONOR_CLASS_LIST:
                new_classification = config.VIRTUAL_CLASS_TRANSLATION[classification]
                extra_points.loc[extra_points['classification'] == classification, 'classification'] \
                    = new_classification

        new_points.classification = extra_points["classification"]
        output_las.append_points(new_points)


def patchwork(config: DictConfig):
    complementary_bd_points = get_complementary_points(config)
    append_points(config, complementary_bd_points)
