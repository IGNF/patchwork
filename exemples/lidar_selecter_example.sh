# for selecting, cutting and dispatching lidar files for patchwork
python lidar_filepath.py \
filepath.DONOR_DIRECTORY=[path_to_directory_with_donor_files] \
filepath.RECIPIENT_DIRECTORY=[path_to_directory_with_recipient_files] \
filepath.SHP_NAME=[shapefile_name] \
filepath.SHP_DIRECTORY=[path_to_shapefile_file] \
filepath.CSV_NAME=[csv_file_name] \
filepath.CSV_DIRECTORY=[path_to_csv_file] \
filepath.OUTPUT_DIRECTORY=[output_directory_path]

# filepath.DONOR_DIRECTORY: The directory containing all the lidar files that could provide points
# filepath.RECIPIENT_DIRECTORY: The directory containing all the lidar files that could receive points
# filepath.SHP_NAME: the name of the shapefile defining the area used to select the lidar files
# filepath.SHP_DIRECTORY: the directory of the shapefile
# filepath.CSV_NAME: the name of the csv file tin which we link donor and recipient files
# filepath.CSV_DIRECTORY: the directory of the csv file
# filepath.OUTPUT_DIRECTORY: the directory to put all the cut lidar files

