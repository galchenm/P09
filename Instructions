* The **`P09_main_configuration_v4.py`** script
* Generalized paths instead of specific usernames or experiment directories
* All available **usage modes** including `--offline`, `--force`, and `--p` (online)

---

# 📘 **Instruction Manual for Running Data Processing with `P09_main_configuration_v4.py`**

---

## 🔧 **1. Navigate to the Processing Directory**

Open your terminal and run:

```bash
cd /path/to/shared/autoprocessing
```

---

## 📦 **2. Load Required Modules**

Before running any script, load the necessary modules:

```bash
module load maxwell python/3.9 crystfel xray
```

---

## 📝 **3. Edit the Configuration File**

Path:

```bash
/path/to/shared/autoprocessing/configuration.yaml
```

Open it in a text editor and update the following fields:

---

### ✅ a) **Update Detector Center Based on Distance**

Update `ORGX` and `ORGY` according to your detector distance, for example:

| Distance (mm) | ORGX   | ORGY   |
| ------------- | ------ | ------ |
| 213.6         | 1255   | 1158   |
| 313.6         | 1256   | 1158.9 |
| 363.6         | 1256.5 | 1159.3 |

---

### ✅ b) **Set Processed Output Directory**

Use an **absolute path** for safety:

```yaml
processed_directory: "/path/to/your/processed_output"
```

---

### ✅ c) **(Optional) Set Unit Cell File**

If you have known unit cell parameters:

```yaml
cell_file: "/path/to/your_cell_file.cell"
```

If not, leave as:

```yaml
cell_file: "None"
```

---

## 👤 **4. Update Username in Python Script**

Open the script:

```bash
/path/to/shared/autoprocessing/P09_main_configuration_v4.py
```

Find and update:

```python
USER = 'your_username'  # Replace with your actual Maxwell username
```

---

## ▶️ **5. Run the Processing Script**

You can use different modes depending on your needs:

---

### 🔸 **Offline Mode**

```bash
python3 P09_main_configuration_v4.py -i /path/to/configuration.yaml --offline
```

---

### 🔸 **Offline with Block of Runs**

```bash
python3 P09_main_configuration_v4.py -i /path/to/configuration.yaml --offline --f /path/to/block_runs.lst
```

---

### 🔸 **Offline with Force Reprocessing**

```bash
python3 P09_main_configuration_v4.py -i /path/to/configuration.yaml --offline --f /path/to/block_runs.lst --force
```

---

### 🔸 **Online Mode**

```bash
python3 P09_main_configuration_v4.py -i /path/to/configuration.yaml --p /path/to/raw/data/folder
```

---

## 📊 **6. Extract Processing Results**

In a new terminal:

```bash
cd /path/to/shared/autoprocessing
python3 logbook_v2.py /path/to/your/processed_output
```
