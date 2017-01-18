import datetime
import glob
import logging
import os
import magic  # python-magic
import nibabel
from nibabel import filebasedimages

from . import connection
from . import dicom_import
from . import nifti_import
from .lren_nifti_path_extractor import LRENNiftiPathExtractor


########################################################################################################################
# SETTINGS
########################################################################################################################

ACQUISITION_STEP_NAME = 'acquisition'
VISIT_STEP_NAME = 'visit'


########################################################################################################################
# MAIN FUNCTIONS
########################################################################################################################

def visit(folder, provenance_id, previous_step_id=None, db_url=None):
    """
    Record all files from a folder into the database.
    The files are listed in the DB. If a file has been copied from previous step without any transformation, it will be
    detected and marked in the DB. The type of file will be detected and stored in the DB. If a files (e.g. a DICOM
    file) contains some meta-data, those will be stored in the DB.
    :param folder: folder path.
    :param provenance_id: provenance label.
    :param previous_step_id: (optional) previous processing step ID. If not defined, we assume this is the first
    processing step.
    :param db_url: (optional) Database URL. If not defined, it looks for an Airflow configuration file.
    :return: return processing step ID.
    """
    logging.info("Connecting to database...")
    db_conn = connection.Connection(db_url)

    if not previous_step_id:
        step_id = create_step(db_conn, ACQUISITION_STEP_NAME, provenance_id)
        record_files(db_conn, folder, step_id)
    else:
        step_id = create_step(db_conn, VISIT_STEP_NAME, provenance_id, previous_step_id)
        visit_results(db_conn, folder, step_id)

    logging.info("Closing database connection...")
    db_conn.close()

    return step_id


def create_provenance(dataset, matlab_version=None, spm_version=None, spm_revision=None, fn_called=None,
                      fn_version=None, others=None, db_url=None):
    """
    Create (or get if already exists) a provenance entity, store it in the database and get back a provenance ID.
    :param dataset: Name of the data set.
    :param matlab_version: (optional) Matlab version.
    :param spm_version: (optional) SPM version.
    :param spm_revision: (optional) SPM revision.
    :param fn_called: (optional) Function called.
    :param fn_version: (optional) Function version.
    :param others: (optional) Any other information can be set using this field.
    :param db_url: (optional) Database URL. If not defined, it looks for an Airflow configuration file.
    :return: Provenance ID.
    """
    logging.info("Connecting to database...")
    db_conn = connection.Connection(db_url)

    provenance = db_conn.db_session.query(db_conn.Provenance).filter_by(
        dataset=dataset, matlab_version=matlab_version, spm_version=spm_version, spm_revision=spm_revision,
        fn_called=fn_called, fn_version=fn_version, others=others
    ).first()

    if not provenance:
        provenance = db_conn.Provenance(
            dataset=dataset, matlab_version=matlab_version, spm_version=spm_version, spm_revision=spm_revision,
            fn_called=fn_called, fn_version=fn_version, others=others
        )
        db_conn.db_session.add(provenance)
        db_conn.db_session.commit()

    provenance_id = provenance.id

    logging.info("Closing database connection...")
    db_conn.close()

    return provenance_id


########################################################################################################################
# SECONDARY FUNCTIONS
########################################################################################################################

def create_step(db_conn, name, provenance_id, previous_step_id=None):
    """
    Create (or get if already exists) a processing step entity, store it in the database and get back a step ID.
    :param db_conn: Database connection.
    :param name: Step name.
    :param provenance_id: Provenance ID.
    :param previous_step_id: Previous processing step ID.
    :return: Step ID.
    """
    step = db_conn.db_session.query(db_conn.ProcessingStep).filter_by(
        name=name, provenance_id=provenance_id, previous_step_id=previous_step_id
    ).first()

    if not step:
        step = db_conn.ProcessingStep(
            name=name, provenance_id=provenance_id, previous_step_id=previous_step_id
        )
        db_conn.db_session.add(step)
        db_conn.db_session.commit()

    step.execution_date = datetime.datetime.now()
    db_conn.db_session.commit()

    return step.id


def record_files(db_conn, folder, step_id):
    """
    Scan folder looking for files. Find type, meta-data, etc. Store all those data in a DB.
    :param db_conn: Database connection.
    :param folder: Folder to scan.
    :param step_id: Step ID.
    :return:
    """
    nifti_path_extractor = LRENNiftiPathExtractor  # TODO: replace this to use BIDS

    for file_path in glob.iglob(os.path.join(folder, "**/*"), recursive=True):
        file_type = find_type(file_path)
        if "DICOM" == file_type:
            dicom_import.dicom2db(file_path, file_type, step_id, db_conn)
        elif "NIFTI" == file_type:
            nifti_import.nifti2db(file_path, file_type, step_id, nifti_path_extractor, db_conn)


def find_type(file_path):
    """
    Get file type.
    :param file_path: File path
    :return: Type (can be DICOM, NIFTI, other, ...). If file_path is not a directory, returns None.
    """
    try:
        file_type = magic.from_file(file_path)
        if "DICOM medical imaging data" == file_type:
            return "DICOM"
        elif "data" == file_type:
            try:
                nibabel.load(file_path)
                return "NIFTI"
            except nibabel.filebasedimages.ImageFileError:
                logging.info("found a file of type 'data' but does not seem to be NIFTI : " + file_path)
        else:
            logging.info("found a file with unhandled type (%s) : %s" % (file_type, file_path))
    except IsADirectoryError:
        return None

    return "other"


def visit_results(db_conn, folder, step_id):
    """
    TODO
    :param db_conn:
    :param folder:
    :param provenance_id:
    :param step_id:
    :return:
    """
    pass
