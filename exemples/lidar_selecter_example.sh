# for selecting, cutting and dispatching lidar files for patchwork
python lidar_filepath.py \
filepath.SHAPEFILE_PATH=[path_to_shapfile] \
filepath.DONOR_DIRECTORY=[path_to_directory_with_donor_files] \
filepath.RECIPIENT_DIRECTORY=[path_to_directory_with_recipient_files] \
filepath.OUTPUT_DIRECTORY_PATH=[output_directory_path]

# filepath.SHAPEFILE_PATH: the shapefile that contains the geometry we want to work on
# filepath.DONOR_DIRECTORY: The directory containing all the lidar files that could provide points
# filepath.RECIPIENT_DIRECTORY: The directory containing all the lidar files that could receive points
# filepath.OUTPUT_DIRECTORY_PATH: the directory to put all the selected/cut lidar files