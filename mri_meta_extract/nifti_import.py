import logging
import re

from datetime import date, datetime

########################################################################################################################
# GLOBAL
########################################################################################################################

conn = None


########################################################################################################################
# FUNCTIONS - NIFTI
########################################################################################################################

def nifti2db(file_path, file_type, step_id, nifti_path_extractor, db_conn):
    global conn
    conn = db_conn
    logging.info("Processing '%s'" % file_path)
    try:
        session = str(re.findall(
            '/([^/]+?)/[^/]+?/[^/]+?/[^/]+?\.nii', file_path)[0])
        sequence = re.findall(
            '/([^/]+?)/[^/]+?/[^/]+?\.nii', file_path)[0]
        repetition = int(re.findall(
            '/([^/]+?)/[^/]+?\.nii', file_path)[0])

        logging.info("SEQUENCE : " + sequence)

        if participant_id and scan_date:

            filename = re.findall('/([^/]+?)\.nii', file_path)[0]

            try:
                prefix_type = re.findall('(.*)PR', filename)[0]
            except IndexError:
                prefix_type = "unknown"

            try:
                postfix_type = re.findall('-\d\d_(.+)', filename)[0]
            except IndexError:
                postfix_type = "unknown"

            save_nifti_meta(
                participant_id,
                scan_date,
                session,
                sequence,
                repetition,
                prefix_type,
                postfix_type,
                file_path,
                file_type,
                step_id
            )

    except ValueError:
        logging.warning(
            "A problem occurred with '%s' ! Check the path format... " % file_path)

    conn.close()
    logging.info('[FINISH]')


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
        processing_step_id
):
    if not conn.db_session.query(conn.DataFile).filter_by(path=file_path).first():

        scan = conn.db_session.query(conn.Scan).filter_by(date=scan_date, participant_id=participant_id)\
            .first()
        sequence_type_list = conn.db_session.query(
            conn.SequenceType).filter_by(name=sequence).all()

        if scan and len(sequence_type_list) > 0:
            scan_id = scan.id
            sess = conn.db_session.query(conn.Session).filter_by(
                scan_id=scan_id, value=session).first()

            if sess:
                session_id = sess.id
                if len(sequence_type_list) > 1:
                    logging.warning(
                        "Multiple sequence_type available for %s !" % sequence)
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
                            repetition_id=repetition_id,
                            processing_step_id=processing_step_id,
                            result_type=prefix_type,
                            output_type=postfix_type
                        )
                        conn.db_session.add(nii)
                        conn.db_session.commit()
