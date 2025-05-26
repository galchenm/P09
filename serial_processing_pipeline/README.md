## 🔧 CrystFEL Data Processing Workflow

### 1. **Generate List of Files and Folder Structure**

Create a file list for each run or a block of runs, and set up the required folder structure:

```bash
python3 auto_creating_list_of_files_with_folder_structure_for_processing.py \
  -i [path_to_raw_data] \
  -l [output_path_for_file_lists] \
  [-p filename_pattern] \
  [-fe file_extension] \
  [-b block_of_interest] \
  [-r processing_structure_output_path]
```

---

### 2. **Initial Processing with Turbo-Index**

If you're using a **single geometry file** for all runs:

```bash
python3 run_turbo_index.py \
  [path_to_processing_structure] \
  [path_to_file_lists] \
  [path_to_turbo_index_script] \
  [-f block_of_interest] \
  [-r]  # Use this flag to rerun processing with new parameters
```

---

### 3. **Merge and Evaluate Streams + Detector Shift Estimation**

Run this to:

* Merge streams
* Generate plots for evaluation (e.g. detector distance)
* Estimate detector shift (optional)
* Auto-generate per-run geometry files

```bash
python3 rerun-merge-detector-shift-v2.py \
  [path_to_processing_structure] \
  [-f block_of_interest] \
  [-pref merged_stream_prefix] \
  [-suf merged_stream_suffix] \
  [--s]  # Skip already merged folders
  [--r]  # Rerun for unprocessed files
  [--d]  # Run detector-shift
```

---

### 4. **Reprocess with Per-Run Geometries (Optional)**

If you generated run-specific geometry files in step 3, re-run turbo-index with:

```bash
python3 run_turbo_index-v2.py \
  [path_to_processing_structure] \
  [path_to_file_lists] \
  [path_to_turbo_index_script] \
  [-f block_of_interest] \
  [--r]  # Rerun unprocessed jobs
  [-pg path_to_run_specific_geometries]
```

---

### 5. **Run Partialator or Create MTZ File**

This script handles partialator or direct MTZ creation:

```bash
python3 partial-mtz.py \
  [path_to_processing_structure] \
  [path_to_script_for_partialator_or_mtz] \
  [-f block_of_interest] \
  [--no-mtz]  # Use if only running partialator
```

---

### 6. **Generate Table 1 (Overall Statistics)**

To compile results across all blocks into a single summary table:

```bash
python3 for_paper_table_generator.py \
  [path_to_processed_data_folder] \
  [output_table_file]
```

---

### 7. **Evaluate Final Data Quality (compare\_hkl & check\_hkl)**

To run final statistics with customizable resolution and binning:

```bash
python3 overallstatistics_with_new_cut_off.py \
  [path_to_hkl_file] \
  [-r high_resolution_limit] \
  [-n number_of_resolution_shells]
```
