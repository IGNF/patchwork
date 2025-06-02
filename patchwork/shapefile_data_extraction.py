import fnmatch
import os

import geopandas as gpd


def get_donor_info_from_shapefile(input_shapefile: str, x: int, y: int, tile_subdirectory: str) -> gpd.GeoDataFrame:
    """Retrieve paths to all the donor files associated with a given tile (with origin x, y) from a shapefile.

    The shapefile should contain one geometry per donor file, with attributes:
        - x: string for the x coordinate of the tile
        (can be expressed in km, the unit is defined using x_y_to_meters_factor)
        - y: string for the y coordinate of the tile
        (can be expressed in km, the unit is defined using x_y_to_meters_factor)
        - nom_coord: string indicating if the coordinates are expected to be found in the filename
        - nuage_mixa: path to the directory that contains the donor file

    The filename for each donor is found using pattern matching using {x}_{y} in the {nuage_mixa}/{tile_subdirectory}
    directory.

    It is stored in the "full_path" column of the output geodataframe

    Args:
        input_shapefile (str): Shapefile describing donor files
        x (int): x coordinate of the tile for which to get the donors
        (in the same unit as in the shapefile, usually km)
        y (int): y coordinate of the tile for which to get the donors
        (in the same unit as in the shapefile, usually km)
        tile_subdirectory (str): subdirectory of "nuage_mixa" in which the donor files are stored

    Raises:
        NotImplementedError: if nom_coord is false (case not handled)
        FileNotFoundError: if path {nuage_mixa}/{tile_subdirectory} does not exist or is not a directory
        FileNotFoundError: if there is no file corresponding to coordinates {x}_{y} in {nuage_mixa}/{tile_subdirectory}
        RuntimeError: if there is several file corresponding to coordinates {x}_{y} in {nuage_mixa}/{tile_subdirectory}

    Returns:
        gpd.GeoDataFrame: geodataframe with columns ["x", "y", "full_path", "geometry"] for each donor file for the
          x, y tile
    """
    gdf = gpd.GeoDataFrame.from_file(input_shapefile, encoding="utf-8")
    gdf = gdf[(gdf["x"].astype(int) == x) & (gdf["y"].astype(int) == y)]

    if not gdf["nom_coord"].isin(["oui", "yes", "true"]).all():
        unsupported_geometries = gdf[(~gdf["nom_coord"].isin(["oui", "yes", "true"]))]
        raise NotImplementedError(
            "Patchwork currently works only if coordinates are contained in the las/laz names, "
            "which is an information store in the 'nom_coord' attribute). "
            f"The following geometries do not match this requirement: {unsupported_geometries}"
        )

    if len(gdf.index):

        def find_las_path_from_geometry_attributes(x: int, y: int, path_root: str):
            tile_directory = os.path.join(path_root, tile_subdirectory)
            if not os.path.isdir(tile_directory):
                raise FileNotFoundError(f"Directory {tile_directory} not found")
            potential_filenames = fnmatch.filter(os.listdir(tile_directory), f"*{x}_{y}*.la[sz]")
            if not potential_filenames:
                raise FileNotFoundError(
                    f"Could not match any file with directory {tile_directory} and coords ({x}, {y})"
                )
            if len(potential_filenames) > 1:
                raise RuntimeError(
                    f"Found multiple files for directory {tile_directory} and coords ({x}, {y}): {potential_filenames}"
                )

            return os.path.join(tile_directory, potential_filenames[0])

        gdf["full_path"] = gdf.apply(
            lambda row: find_las_path_from_geometry_attributes(row["x"], row["y"], row["nuage_mixa"]),
            axis="columns",
        )

    else:
        gdf = gpd.GeoDataFrame(columns=["x", "y", "full_path", "geometry"])

    return gdf[["x", "y", "full_path", "geometry"]]
