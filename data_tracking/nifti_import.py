import logging
import re

from . import utils


#######################################################################################################################
# PUBLIC FUNCTIONS
#######################################################################################################################

def nifti2db(file_path, file_type, is_copy, step_id, db_conn, sid_by_patient=False, pid_in_vid=False):
    """Extract some meta-data from NIFTI files (actually mostly from their paths) and stores it in a DB.

    Arguments:
    :param file_path: File path.
    :param file_type: File type.
    :param is_copy: Indicate if this file is a copy.
    :param step_id: Step ID.
    :param db_conn: Database connection.
    :param sid_by_patient: Rarely, a data set might use study IDs which are unique by patient
    (not for the whole study).
    E.g.: LREN data. In such a case, you have to enable this flag. This will use PatientID + StudyID as a session ID.
    :param pid_in_vid: Rarely, a data set might mix patient IDs and visit IDs. E.g. : LREN data. In such a case, you
    to enable this flag. This will try to split PatientID into VisitID and PatientID.
    :return:
    """
    logging.info("Processing '%s'" % file_path)

    df = db_conn.db_session.query(db_conn.DataFile).filter_by(path=file_path).one_or_none()

    if not df:

        dataset = db_conn.get_dataset(step_id)
        _extract_participant(db_conn, file_path, pid_in_vid, dataset)
        visit_id = _extract_visit(db_conn, file_path, pid_in_vid, sid_by_patient, dataset)
        session_id = _extract_session(db_conn, file_path, visit_id)
        sequence_id = _extract_sequence(db_conn, file_path, session_id)
        repetition_id = _extract_repetition(db_conn, file_path, sequence_id)

        df = db_conn.DataFile(
            path=file_path,
            type=file_type,
            is_copy=is_copy,
            processing_step_id=step_id,
            repetition_id=repetition_id
        )
        db_conn.db_session.add(df)
        db_conn.db_session.commit()


#######################################################################################################################
# PRIVATE FUNCTIONS
#######################################################################################################################

def _extract_participant(db_conn, file_path, pid_in_vid, dataset):
    participant_name = str(re.findall('/([^/]+?)/[^/]+?/[^/]+?/[^/]+?/[^/]+?\.nii', file_path)[0])
    if pid_in_vid:
        try:
            participant_name = utils.split_patient_id(participant_name)[1]
        except TypeError:
            pass
    participant_id = db_conn.get_participant_id(participant_name, dataset)

    # Sync participant table with participant_mapping table
    participant = db_conn.db_session.query(db_conn.Participant).filter_by(id=participant_id).one_or_none()
    if not participant:
        participant = db_conn.Participant(
            id=participant_id
        )
        db_conn.db_session.add(participant)
    return participant_id


def _extract_session(db_conn, file_path, visit_id):
    try:
        session = str(re.findall('/([^/]+?)/[^/]+?/[^/]+?/[^/]+?\.nii', file_path)[0])
    except AttributeError:
        logging.debug("Field StudyID was not found")
        session = None
    return db_conn.get_session_id(session, visit_id)


def _extract_sequence(db_conn, file_path, session_id):
    sequence_name = str(re.findall('/([^/]+?)/[^/]+?/[^/]+?\.nii', file_path)[0])
    return db_conn.get_sequence_id(sequence_name, session_id)


def _extract_visit(db_conn, file_path, pid_in_vid, by_patient, dataset):
    participant_name = str(re.findall('/([^/]+?)/[^/]+?/[^/]+?/[^/]+?/[^/]+?\.nii', file_path)[0])
    visit_name = None
    if pid_in_vid:  # If the patient ID and the visit ID are mixed into the PatientID field (e.g. LREN data)
        try:
            visit_name = utils.split_patient_id(participant_name)[0]
        except TypeError:
            visit_name = None
    if not pid_in_vid or not visit_name:  # Otherwise, we use the StudyID (also used as a session ID) (e.g. PPMI data)
        try:
            visit_name = str(re.findall('/([^/]+?)/[^/]+?/[^/]+?/[^/]+?\.nii', file_path)[0])
            if by_patient:  # If the Study ID is given at the patient level (e.g. LREN data), here is a little trick
                visit_name = participant_name + "_" + visit_name
        except AttributeError:
            logging.debug("Field StudyID was not found")
            visit_name = None

    visit_id = db_conn.get_visit_id(visit_name, dataset)

    # Sync visit table with visit_mapping table
    participant_id = db_conn.get_participant_id(participant_name, dataset)
    visit = db_conn.db_session.query(db_conn.Visit).filter_by(id=visit_id).one_or_none()
    if not visit:
        visit = db_conn.Visit(
            id=visit_id,
            participant_id=participant_id,
        )
        db_conn.db_session.add(visit)

    return visit_id


def _extract_repetition(db_conn, file_path, sequence_id):
    repetition_name = str(re.findall('/([^/]+?)/[^/]+?\.nii', file_path)[0])
    return db_conn.get_repetition_id(repetition_name, sequence_id)
