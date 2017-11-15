import builtins
import logging
import os
import datetime
import glob
import hashlib
import sys
import fnmatch

# magic refers to the python-magic library
import magic

import nibabel
from nibabel import filebasedimages

from . import connection
from . import dicom_import
from . import nifti_import
from . import others_import


##########################################################################
# SETTINGS
##########################################################################

HASH_BLOCK_SIZE = 65536  # Avoid getting out of memory when hashing big files


##########################################################################
# PUBLIC FUNCTIONS
##########################################################################

def visit(folder, provenance_id, step_name, previous_step_id=None, config=None, db_url=None, is_organised=True):
    """Record all files from a folder into the database.

    Note:
    If a file has been copied from a previous processing step without any transformation, it will be detected and
    marked in the DB. The type of file will be detected and stored in the DB (NIFTI, DICOM, ...). If a files
    (e.g. a DICOM file) contains some meta-data, those will be stored in the DB.

    Arguments:
    :param folder: folder path.
    :param provenance_id: provenance label.
    :param step_name: Name of the processing step that produced the folder to visit.
    :param previous_step_id: (optional) previous processing step ID. If not defined, we assume this is the first
    processing step.
    :param config: List of flags:
        - boost: (optional) When enabled, we consider that all the files from a same folder share the same meta-data.
        When enabled, the processing is (about 2 times) faster. This option is enabled by default.
        - session_id_by_patient: Rarely, a data set might use study IDs which are unique by patient (not for the whole
        study).
        E.g.: LREN data. In such a case, you have to enable this flag. This will use PatientID + StudyID as a session
        ID.
        - visit_id_in_patient_id: Rarely, a data set might mix patient IDs and visit IDs. E.g. : LREN data. In such a
        case, you have to enable this flag. This will try to split PatientID into VisitID and PatientID.
        - visit_id_from_path: Enable this flag to get the visit ID from the folder hierarchy instead of DICOM meta-data
        (e.g. can be useful for PPMI).
        - repetition_from_path: Enable this flag to get the repetition ID from the folder hierarchy instead of DICOM
        meta-data (e.g. can be useful for PPMI).
    :param db_url: (optional) Database URL. If not defined, it looks for an Airflow configuration file.
    :param is_organised: (optional) Disable this flag when scanning a folder that has not been organised yet
    (should only affect nifti files).
    :return: return processing step ID.
    """
    config = config if config else []

    logging.info("Visiting %s", folder)
    logging.info("-> is_organised=%s", str(is_organised))
    logging.info("-> config=%s", str(config))

    logging.info("Connecting to database...")
    db_conn = connection.Connection(db_url)

    step_id = _create_step(db_conn, step_name, provenance_id, previous_step_id)

    previous_files_hash = _get_files_hash_from_step(db_conn, previous_step_id)

    checked = dict()

    def process_file(file_path):
        logging.debug("Processing '%s'" % file_path)
        file_type = _find_type(file_path)
        if "DICOM" == file_type:
            is_copy = _hash_file(file_path) in previous_files_hash
            leaf_folder = os.path.split(file_path)[0]
            if leaf_folder not in checked or 'boost' not in config:
                ret = dicom_import.dicom2db(file_path, file_type, is_copy, step_id, db_conn,
                                            'session_id_by_patient' in config, 'visit_id_in_patient_id' in config,
                                            'visit_id_in_patient_id' in config, 'repetition_from_path' in config)
                try:
                    checked[leaf_folder] = ret['repetition_id']
                except KeyError:
                    # TODO: Remove it when dicom2db will be more stable
                    logging.warning("Cannot find repetition ID !")
            else:
                dicom_import.extract_dicom(
                    file_path, file_type, is_copy, checked[leaf_folder], step_id)
        elif "NIFTI" == file_type and is_organised:
            is_copy = _hash_file(file_path) in previous_files_hash
            nifti_import.nifti2db(file_path, file_type, is_copy, step_id, db_conn, 'session_id_by_patient' in config,
                                  'visit_id_in_patient_id' in config)
        elif file_type:
            is_copy = _hash_file(file_path) in previous_files_hash
            others_import.others2db(
                file_path, file_type, is_copy, step_id, db_conn)

    if sys.version_info.major == 3 and sys.version_info.minor < 5:
        matches = []
        for root, dirnames, filenames in os.walk(folder):
            for filename in fnmatch.filter(filenames, '*'):
                matches.append(os.path.join(root, filename))
        for file_path in matches:
            process_file(file_path)
    else:
        for file_path in glob.iglob(os.path.join(folder, "**/*"), recursive=True):
            process_file(file_path)

    logging.info("Closing database connection...")
    db_conn.close()

    return step_id


def create_provenance(dataset, software_versions=None, db_url=None):
    """Create (or get if already exists) a provenance entity, store it in the database and get back a provenance ID.

    Arguments:
    :param dataset: Name of the data set.
    :param software_versions: (optional) Version of the software components used to get the data. It is a dictionary
    that accepts the following fields:
        - matlab_version
        - spm_version
        - spm_revision
        - fn_called
        - fn_version
        - others
    :param db_url: (optional) Database URL. If not defined, it looks for an Airflow configuration file.
    :return: Provenance ID.
    """
    logging.info("Connecting to database...")
    db_conn = connection.Connection(db_url)

    try:
        matlab_version = software_versions['matlab_version']
    except (KeyError, TypeError):
        matlab_version = None
    try:
        spm_version = software_versions['spm_version']
    except (KeyError, TypeError):
        spm_version = None
    try:
        spm_revision = software_versions['spm_revision']
    except (KeyError, TypeError):
        spm_revision = None
    try:
        fn_called = software_versions['fn_called']
    except (KeyError, TypeError):
        fn_called = None
    try:
        fn_version = software_versions['fn_version']
    except (KeyError, TypeError):
        fn_version = None
    try:
        others = software_versions['others']
    except (KeyError, TypeError):
        others = None

    provenance = db_conn.db_session.query(db_conn.Provenance).filter_by(
        dataset=dataset, matlab_version=matlab_version, spm_version=spm_version, spm_revision=spm_revision,
        fn_called=fn_called, fn_version=fn_version, others=others
    ).first()

    if not provenance:
        provenance = db_conn.Provenance(
            dataset=dataset, matlab_version=matlab_version, spm_version=spm_version, spm_revision=spm_revision,
            fn_called=fn_called, fn_version=fn_version, others=others
        )
        db_conn.db_session.merge(provenance)
        db_conn.db_session.commit()

        provenance = db_conn.db_session.query(db_conn.Provenance).filter_by(
            dataset=dataset, matlab_version=matlab_version, spm_version=spm_version, spm_revision=spm_revision,
            fn_called=fn_called, fn_version=fn_version, others=others
        ).first()

    provenance_id = provenance.id

    logging.info("Closing database connection...")
    db_conn.close()

    return provenance_id


##########################################################################
# PRIVATE FUNCTIONS
##########################################################################

def _create_step(db_conn, name, provenance_id, previous_step_id=None):
    step = db_conn.db_session.query(db_conn.ProcessingStep).filter_by(
        name=name, provenance_id=provenance_id, previous_step_id=previous_step_id
    ).first()

    if not step:
        step = db_conn.ProcessingStep(
            name=name, provenance_id=provenance_id, previous_step_id=previous_step_id
        )
        db_conn.db_session.merge(step)
        db_conn.db_session.commit()

        step = db_conn.db_session.query(db_conn.ProcessingStep).filter_by(
            name=name, provenance_id=provenance_id, previous_step_id=previous_step_id
        ).first()

    step.execution_date = datetime.datetime.now()
    db_conn.db_session.commit()

    return step.id


def _find_type(file_path):
    try:
        file_type = magic.from_file(file_path)
        if "DICOM medical imaging data" == file_type:
            return "DICOM"
        elif "data" == file_type:
            try:
                nibabel.load(file_path)
                return "NIFTI"
            except filebasedimages.ImageFileError:
                logging.info(
                    "found a file of type 'data' but does not seem to be NIFTI : " + file_path)
        else:
            logging.info("found a file with unhandled type (%s) : %s" %
                         (file_type, file_path))
    except builtins.IsADirectoryError:
        return None

    return "other"


def _get_files_hash_from_step(db_conn, step_id):
    files = db_conn.db_session.query(db_conn.DataFile).filter_by(
        processing_step_id=step_id).all()
    return [_hash_file(file.path) for file in files]


def _hash_file(filename):
    hasher = hashlib.sha1()
    try:
        with open(filename, 'rb') as f:
            buf = f.read(HASH_BLOCK_SIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(HASH_BLOCK_SIZE)
        return hasher.hexdigest()
    except OSError:
        return None
