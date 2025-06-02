from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Dict, List


def get_mounted_path_from_raw_path(raw_path: str, mount_points: List[Dict]):
    """Get mounted path from a raw path and a list of mount points.
    In case the raw path does not correspond to any mount point, the input raw_path is returned.

    Each mount point is described in a dictionary with keys:
    - ORIGINAL_PATH (str): Original path of the mounted directory (root of the raw path to replace)
    - MOUNTED_PATH (str): Mounted path of the directory (root path by which to replace the root of the raw path
    in order to access to the directory on the current computer)
    - ORIGINAL_PLATFORM_IS_WINDOWS (bool): true if the raw path should be interpreted as a windows path
    when using this mount point

    Args:
        raw_path (str): Original path to convert to a mounted path
        mount_points (List[Dict]): List of mount points (as described above)
    """
    mounted_path = None
    for mount_point in mount_points:
        mounted_path = get_mounted_path_from_mount_point(raw_path, mount_point)
        if mounted_path is not None:
            break
    if mounted_path is None:
        mounted_path = Path(raw_path)

    return mounted_path


def get_mounted_path_from_mount_point(raw_path, mount_point):
    out_path = None
    PureInputPath = PureWindowsPath if mount_point["ORIGINAL_PLATFORM_IS_WINDOWS"] else PurePosixPath
    if PureInputPath(raw_path).is_relative_to(PureInputPath(mount_point["ORIGINAL_PATH"])):
        relative_path = PureInputPath(raw_path).relative_to(PureInputPath(mount_point["ORIGINAL_PATH"]))
        out_path = mount_point["MOUNTED_PATH"] / Path(relative_path)

    return out_path
