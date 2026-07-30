# SmartTable

Repository containing all code, processing pipelines, GUI components, and documentation for the SmartTable plant phenotyping system.

---

## Repository Structure

```text
SmartTable/
├── SmartTableTutorial/
├── Code/
├── RGB_2_BIN/
├── extract_feature_points/
├── extract_vectors_from_csv/
├── newGui/
├── mergeData/
└── main
```

---

## Directory Overview

### 📖 `SmartTableTutorial`
Contains all files pertaining to LaTeX manual.

---

### 💻 `Code`
Contains old files used to originally mask images as well as code to run the tables.

---

### 🖼️ `RGB_2_BIN`
Processing pipeline to create binary images.

---

### 📍 `extract_feature_points`
Performs Shi-Tomasi and Lucas-Kanade to generate tracked points along perimeter of plant.

---

### 📈 `extract_vectors_from_csv`
Performs all analysis as well as calculating motion.

---

### 🖥️ `newGui`
New graphical user interface, handles running all code blocks.

---

### 📊 `mergeData`
Handles merging all folder specific excel files into a single excel file for the parent directory.

---

### ▶️ `main`
Runs everything.
