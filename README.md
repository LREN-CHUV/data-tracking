## What is it ?

This project contains some scripts that extract some metadata from DICOM files, NIFTI files and spreadsheets,
and import them into a database.

## What does it require ?

* [Python3.5](https://www.python.org/);
* [pydicom](http://pydicom.readthedocs.org/en/latest/getting_started.html);
* [SQLAlchemy](http://www.sqlalchemy.org/);
* [Alembic](http://alembic.readthedocs.io/en/latest/);
* [MySQL](http://www.mysql.com/);
* [PyMySQL](https://github.com/PyMySQL/PyMySQL).

## How does it work ?

### Deploy/Upgrade the database

(You need to `cd data/db/` and configure alembic prior to run it. See: alembic.ini.)

1. Create a schema like this: `mysql -p -e 'CREATE SCHEMA IF NOT EXISTS mri'`;
2. Create/Upgrade the schema: `alembic upgrade head`.

Note: You can destroy the database like this: `mysql -p -e 'DROP SCHEMA mri'`.

### Import from DICOM

(You need to `cd src/` prior to run it or precise the path to the scripts.)

To extract data from files using anonymized ID values, run: `python2.7 extract-dicom.py <dir> <db>`.

To extract data from files using PR***** ID values, run: `python2.7 extract-dicom.py <dir> <db> -i <csv>`
where 'csv' is a file containing at least | PR***** | anonym_ID |. You can generate such a file using the 
[anonymizer](http://hbps1.intranet.chuv:7000/LREN/anonymizer) project.

NOTE: This project does not provide DICOM files for testing.

### Import from NIFTI

(You need to `cd src/` prior to run it or precise the path to the scripts)

Run: `python2.7 extract-nifti.py <dir> <csv> <db>`
where 'csv' is a file containing at least | PR***** | anonym_ID | scan_date |. You can generate such a file using the 
[anonymizer](http://hbps1.intranet.chuv:7000/LREN/anonymizer) project.

NOTE: To generate a mock directories structure for testing, you can run: `python2.7 test/create_dir_struct.py <csv>`
where 'csv' is a dump file. You can generate such a file running something like that in a PowerShell:
`PS M:\CRN\LREN\SHARE\VBQ_Output_All> Get-ChildItem -Recurse .\MPMs_All | ForEach-Object {$_ | add-member -name "Owner" -
membertype noteproperty -value (get-acl $_.fullname).owner -passthru} | Sort-Object fullname | Select FullName,CreationT
ime,LastWriteTime,Length,Owner | Export-Csv -Force -NoTypeInformation ..\list_files.csv`.

### Import from spreadsheets

(You need to `cd src/` prior to run it or precise the path to the scripts.)

To extract data from a spreadsheet formatted like | anonymized_ID | ... |,
run: `python2.7 extract-more.py <file> <sheet> <db>`.

To extract data from a spreadsheet formatted like | PR***** | ... |,
run: `python2.7 extract-more.py <file> <sheet> <db> -i <csv>`
where 'csv' is a file containing at least | PR***** | anonym_ID |. You can generate such a file using the 
[anonymizer](http://hbps1.intranet.chuv:7000/LREN/anonymizer) project.

## Usage example

You can customize the three following scripts to avoid typing too much commands:

* db_init.sh - Clear and recreate the database;
* extract.sh - Extract data from dcm, nii and xls;
* run.sh - Run db_init.sh and extract.sh
