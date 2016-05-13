#!/usr/bin/env bash

echo "IMPORT from DICOM files"
python3.5 src/extract-dicom.py /home/mirco/DICOM mysql+pymysql://mirco:pass@localhost:3306/mri -i data/spreadsheets/anonymized.csv

echo "IMPORT from NIFTI files"
python3.5 src/extract-nifti.py src/test/data/ data/spreadsheets/PR_ID_ScanDate.csv mysql+pymysql://mirco:pass@localhost:3306/mri

echo "IMPORT from spreadsheet"
python3.5 src/extract-more.py data/spreadsheets/LREN_Server_data_info_All_Data_16Feb2016095705.xls Data mysql+pymysql://mirco:pass@localhost:3306/mri -i data/spreadsheets/anonymized.csv
