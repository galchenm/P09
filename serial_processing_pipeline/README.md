1. Create list of files for each run or for block of runs and the folder structure by running the following script:

python3 auto_creating_list_of_files_with_folder_structure_for_processing.py -i [path_to_raw_data] -l [path_where_you_will_keep_all_list_of_files] [-p pattern_in_filename, optional]  [-fe file_extension, optional] [-b block_of_interest, optional] [-r path_to_the_folder_for_creating_structure_for_further_processing]

2. Run the turbo-index script (https://www.desy.de/~twhite/crystfel/scripts/turbo-index-slurm) for processing your data by running it with following command line if you have one geometry file for all runs:

python3 run_turbo_index.py [path_to_the_folder_for_creating_structure_for_further_processing, raw processing results] [path to the folder with lists of files] [path to the turbo-index script] [-f block_of_interest] [-r True (if you want to rerun indexing and pf with different parameters)]

3. Use this script for checking and merging streams. This script will also genereta several plots for evaluation such parameters as detector distance.

python3 rerun-merge-detector-shift-v2.py [path_to_the_folder_for_creating_structure_for_further_processing] [-f block_of_interest] [-pref prefix_for_merged_stream] [-suf suffix_for_merged_stream] [--s use this flag if you want to skip folders with already merged stream] [--r use this flag if you want to rerun jobs on the files that were not processed] [--d Use this flag if you want to run detector-shift]

As it was mentioned before, this script will also be able to generate geometry file for each run based on results of the script detector-shift. In this case you can reprocess data with geometry file for each run as following:

python3 run_turbo_index-v2.py [path_to_the_folder_for_creating_structure_for_further_processing] [path_where_you_will_keep_all_list_of_files] [path to the turbo-index script] [-f block_of_interest] [--r use this flag if you want to rerun jobs on the files that were not processed] [-pg path_to_all_geometries_genereted_by rerun-merge-detector-shift-v2.py]

4. Use this script for running partiliator or for create-mtz:

python3 partial-mtz.py [path_to_the_folder_for_creating_structure_for_further_processing] [path_to_the_script_executed_partiliator_or_mtz] [-f block_of_interest] [--no-mtz use this flag if you want to run partiliator]

5. To accumulate all result in Table1 with overall statistics run the following command:

python3 for_paper_table_generator.py [folder with processed data] [file_with_all_results]

There is the script for running compare_hkl and check_hkl on data with getting results in table 1

python3 overallstatistics_with_new_cut_off.py [absolute path to hkl file] [-r highres] [-n number_of_shells]