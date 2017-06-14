import logging


#######################################################################################################################
# PUBLIC FUNCTIONS
#######################################################################################################################

def others2db(file_path, file_type, is_copy, step_id, db_conn):
    """Extract some meta-data from files (actually mostly from their paths) and stores it in a DB.

    Arguments:
    :param file_path: File path.
    :param file_type: File type.
    :param is_copy: Indicate if this file is a copy.
    :param step_id: Step ID.
    :param db_conn: Database connection.
    :return:
    """
    logging.info("Processing '%s'" % file_path)

    df = db_conn.db_session.query(db_conn.DataFile).filter_by(path=file_path).one_or_none()

    if not df:
        df = db_conn.DataFile(
            path=file_path,
            type=file_type,
            is_copy=is_copy,
            processing_step_id=step_id
        )
        db_conn.db_session.merge(df)
        db_conn.db_session.commit()
    else:
        if file_type not in [None, '', df.type]:
            df.type = file_type
            db_conn.db_session.commit()
        if is_copy not in [None, df.is_copy]:
            df.is_copy = is_copy
            db_conn.db_session.commit()
        if step_id not in [None, df.processing_step_id]:
            df.processing_step_id = step_id
            db_conn.db_session.commit()
