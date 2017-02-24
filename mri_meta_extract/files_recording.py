import datetime
import glob
import logging
import os
import hashlib
import magic  # python-magic
import nibabel
from nibabel import filebasedimages

from . import connection
from . import dicom_import
from . import nifti_import
from . import others_import


########################################################################################################################
# SETTINGS
########################################################################################################################

HASH_BLOCK_SIZE = 65536  # Avoid getting out of memory when hashing big files


########################################################################################################################
# PUBLIC FUNCTIONS
########################################################################################################################

def visit(step_name, folder, provenance_id, previous_step_id=None, boost=True, db_url=None, sid_by_patient=False,
          pid_in_vid=False, visit_in_path=False, rep_in_path=False):
    """
    Record all files from a folder into the database.
    If a file has been copied from a previous processing step without any transformation, it will be detected and marked
    in the DB. The type of file will be detected and stored in the DB (NIFTI, DICOM, ...). If a files (e.g. a DICOM
    file) contains some meta-data, those will be stored in the DB.
    :param step_name: Name of the processing step that produced the folder to visit.
    :param folder: folder path.
    :param provenance_id: provenance label.
    :param previous_step_id: (optional) previous processing step ID. If not defined, we assume this is the first
    processing step.
    :param boost: (optional) When enabled, we consider that all the files from a same folder share the same meta-data.
    When enabled, the processing is (about 2 times) faster. This option is enabled by default.
    :param db_url: (optional) Database URL. If not defined, it looks for an Airflow configuration file.
    :param sid_by_patient: Rarely, a data set might use study IDs which are unique by patient (not for the whole study).
    E.g.: LREN data. In such a case, you have to enable this flag. This will use PatientID + StudyID as a session ID.
    :param pid_in_vid: Rarely, a data set might mix patient IDs and visit IDs. E.g. : LREN data. In such a case, you
    to enable this flag. This will try to split PatientID into VisitID and PatientID.
    :param visit_in_path: Enable this flag to get the visit ID from the folder hierarchy instead of DICOM meta-data
    (e.g. can be useful for PPMI).
    :param rep_in_path: Enable this flag to get the repetition ID from the folder hierarchy instead of DICOM meta-data
    (e.g. can be useful for PPMI).
    :return: return processing step ID.
    """
    logging.info("Connecting to database...")
    db_conn = connection.Connection(db_url)

    step_id = _create_step(db_conn, step_name, provenance_id, previous_step_id)

    previous_files_hash = _get_files_hash_from_step(db_conn, previous_step_id)

    checked = dict()
    for file_path in glob.iglob(os.path.join(folder, "**/*"), recursive=True):
        logging.debug("Processing '%s'" % file_path)
        file_type = _find_type(file_path)
        if "DICOM" == file_type:
            is_copy = _hash_file(file_path) in previous_files_hash
            leaf_folder = os.path.split(file_path)[0]
            if leaf_folder not in checked or not boost:
                ret = dicom_import.dicom2db(file_path, file_type, is_copy, step_id, db_conn, sid_by_patient, pid_in_vid,
                                            visit_in_path, rep_in_path)
                checked[leaf_folder] = ret['repetition_id']
            else:
                dicom_import.extract_dicom(file_path, file_type, is_copy, checked[leaf_folder], step_id)
        elif "NIFTI" == file_type:
            is_copy = _hash_file(file_path) in previous_files_hash
            nifti_import.nifti2db(file_path, file_type, is_copy, step_id, db_conn, sid_by_patient, pid_in_vid)
        elif file_type:
            is_copy = _hash_file(file_path) in previous_files_hash
            others_import.others2db(file_path, file_type, is_copy, step_id, db_conn)

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
# PRIVATE FUNCTIONS
########################################################################################################################

def _create_step(db_conn, name, provenance_id, previous_step_id=None):
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


def _find_type(file_path):
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
            except filebasedimages.ImageFileError:
                logging.info("found a file of type 'data' but does not seem to be NIFTI : " + file_path)
        else:
            logging.info("found a file with unhandled type (%s) : %s" % (file_type, file_path))
    except IsADirectoryError:
        return None

    return "other"


def _get_files_hash_from_step(db_conn, step_id):
    files = db_conn.db_session.query(db_conn.DataFile).filter_by(processing_step_id=step_id).all()
    return [_hash_file(file.path) for file in files]


def _hash_file(filename):
    hasher = hashlib.sha1()
    with open(filename, 'rb') as f:
        buf = f.read(HASH_BLOCK_SIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(HASH_BLOCK_SIZE)
    return hasher.hexdigest()
