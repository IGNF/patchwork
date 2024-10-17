# for selecting, cutting and dispatching lidar files for patchwork
python main.py \

filepath.DONOR_FILE=[donor_file_path]
filepath.RECIPIENT_FILE=[recipient_file_path]
filepath.OUTPUT_FILE=[output_file_path]
filepath.OUTPUT_INDICES_MAP=[output_indices_map_path]

# filepath.DONOR_FILE: the path to the lidar file we will add points from
# filepath.RECIPIENT_FILE: the path to the lidar file we will add points to
# filepath.OUTPUT_FILE: the path to the resulting lidar file
# filepath.OUTPUT_INDICES_MAP: the path to the map with indices displaying where points have been added