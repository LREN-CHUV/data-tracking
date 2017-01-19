import logging
import re

from datetime import date


########################################################################################################################
# GLOBAL
########################################################################################################################

conn = None


########################################################################################################################
# FUNCTIONS - NIFTI
########################################################################################################################

def nifti2db(file_path, file_type, is_copy, step_id, nifti_path_extractor, db_conn):
    global conn
    conn = db_conn
    logging.info("Processing '%s'" % file_path)
    save_nifti_meta(
        nifti_path_extractor.extract_participant_id(file_path),
        nifti_path_extractor.extract_scan_date(file_path),
        nifti_path_extractor.extract_session(file_path),
        nifti_path_extractor.extract_sequence(file_path),
        nifti_path_extractor.extract_repetition(file_path),
        nifti_path_extractor.extract_prefix_type(file_path),
        nifti_path_extractor.extract_postfix_type(file_path),
        file_path,
        file_type,
        is_copy,
        step_id
    )


########################################################################################################################
# FUNCTIONS - UTILS
########################################################################################################################

def date_from_str(date_str):
    day = int(re.findall('(\d+)\.\d+\.\d+', date_str)[0])
    month = int(re.findall('\d+\.(\d+)\.\d+', date_str)[0])
    year = int(re.findall('\d+\.\d+\.(\d+)', date_str)[0])
    return date(year, month, day)


########################################################################################################################
# FUNCTIONS - DATABASE
########################################################################################################################

def save_nifti_meta(
        participant_id,
        scan_date,
        session,
        sequence,
        repetition,
        prefix_type,
        postfix_type,
        file_path,
        file_type,
        is_copy,
        processing_step_id
):
    if not conn.db_session.query(conn.DataFile).filter_by(path=file_path).first():

        if scan_date:
            scan = conn.db_session.query(conn.Scan).filter_by(date=scan_date, participant_id=participant_id).first()
        else:
            scan = guess_scan(participant_id)
            if not scan:
                logging.warning("Cannot record file : " + file_path + " ! Cannot find scan date...")
                return

        sequence_type_list = conn.db_session.query(conn.SequenceType).filter_by(name=sequence).all()

        if scan and len(sequence_type_list) > 0:
            scan_id = scan.id
            sess = conn.db_session.query(conn.Session).filter_by(scan_id=scan_id, value=session).first()

            if sess:
                session_id = sess.id
                if len(sequence_type_list) > 1:
                    logging.warning("Multiple sequence_type available for %s !" % sequence)
                sequence_type_id = sequence_type_list[0].id
                seq = conn.db_session.query(conn.Sequence).filter_by(
                    session_id=session_id,
                    sequence_type_id=sequence_type_id)\
                    .first()

                if seq:
                    sequence_id = seq.id
                    rep = conn.db_session.query(conn.Repetition).filter_by(
                        sequence_id=sequence_id,
                        value=repetition)\
                        .first()

                    if rep:
                        repetition_id = rep.id
                        nii = conn.DataFile(
                            path=file_path,
                            type=file_type,
                            is_copy=is_copy,
                            repetition_id=repetition_id,
                            processing_step_id=processing_step_id,
                            result_type=prefix_type,
                            output_type=postfix_type
                        )
                        conn.db_session.add(nii)
                        conn.db_session.commit()


def guess_scan(participant_id):
    scans = conn.db_session.query(conn.Scan).filter_by(participant_id=participant_id).all()
    if len(scans) == 1:
        return scans[0]
    logging.debug("Cannot guess scan date !")
    return None
