import datetime
import logging
from . import connection


########################################################################################################################
# SETTINGS
########################################################################################################################

ACQUISITION_STEP_NAME = 'acquisition'
VISIT_STEP_NAME = 'visit'


########################################################################################################################
# PUBLIC FUNCTION
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
    # logging.info("Running visit function with the following parameters : "
    #              "folder=%s, provenance_id=%s, step_id=%s, db_url=%s",
    #              (folder, provenance_id, previous_step_id, db_url))

    logging.info("Connecting to database...")
    db_conn = connection.Connection(db_url)

    if not previous_step_id:
        step_id = create_step(db_conn, ACQUISITION_STEP_NAME, provenance_id)
        record_files(db_conn, folder, provenance_id, step_id)
    else:
        step_id = create_step(db_conn, VISIT_STEP_NAME, provenance_id, previous_step_id)
        visit_results(db_conn, folder, provenance_id, step_id)

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
    # logging.info("Running create_provenance function with the following parameters : "
    #              "dataset=%s, matlab_version=%s, spm_version=%s, spm_revision=%s, fn_called=%s, fn_version=%s, "
    #              "others=%s, db_url=%s",
    #              (dataset, matlab_version, spm_version, spm_revision, fn_called, fn_version, others, db_url))

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

    logging.info("Closing database connection...")
    db_conn.close()

    return provenance.id


########################################################################################################################
# PRIVATE FUNCTION
########################################################################################################################

def create_step(db_conn, name, provenance_id, previous_step_id=None):
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


def record_files(db_conn, folder, provenance_id, step_id):
    pass


def visit_results(db_conn, folder, provenance_id, step_id):
    pass
