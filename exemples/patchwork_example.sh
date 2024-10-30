# for selecting, cutting and dispatching lidar files for patchwork
python main.py \

filepath.DONOR_DIRECTORY=[donor_file_dir]
filepath.DONOR_NAME=[donor_file_name]
filepath.RECIPIENT_DIRECTORY=[recipient_file_dir]
filepath.RECIPIENT_NAME=[recipient_file_name]
filepath.OUTPUT_DIR=[output_file_dir]
filepath.OUTPUT_NAME=[output_file_name]
filepath.OUTPUT_INDICES_MAP_DIR=[output_indices_map_dir]
filepath.OUTPUT_INDICES_MAP_NAME=[output_indices_map_name]

# filepath.DONOR_DIRECTORY: the directory to the lidar file we will add points from
# filepath.DONOR_NAME: the name of the lidar file we will add points from
# filepath.RECIPIENT_DIRECTORY: the directory to the lidar file we will add points to
# filepath.RECIPIENT_NAME: the name of the lidar file we will add points to
# filepath.OUTPUT_DIR: the directory to the resulting lidar file
# filepath.OUTPUT_NAME: the directory of the resulting lidar file
# filepath.OUTPUT_INDICES_MAP_DIR: the directory to the map with indices displaying where points have been added
# filepath.OUTPUT_INDICES_MAP_NAME: the name of the map with indices displaying where points have been added