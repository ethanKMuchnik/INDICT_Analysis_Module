# Analysis Module

Tools for analyzing INDICT XLSX scoring data.

## Installation
pip install .

## Usage
```python
from analysis_module import INDICT_XLSX_Analysis

INDICT_XLSX_Analysis('scoring.xlsx', 'master.xlsx', save_path='./results/')

## Installing & Using:

**Local install:**
```bash
cd INDICT_Analysis_Module
pip install .

From GitHub (after pushing):
pip install git+https://github.com/ethanmuchnik/INDICT_Analysis_Module.git

Using it:
from analysis_module import INDICT_XLSX_Analysis

INDICT_XLSX_Analysis('../input_data/LabChartScoring.xlsx',
                     '../input_data/Master.xlsx',
                     save_path='../results/')

