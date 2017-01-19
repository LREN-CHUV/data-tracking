import dicom
import datetime
import logging

from sqlalchemy.exc import IntegrityError
from dicom.errors import InvalidDicomError


########################################################################################################################
# SETTINGS
########################################################################################################################

DEFAULT_HANDEDNESS = 'unknown'
DEFAULT_ROLE = 'U'
DEFAULT_COMMENT = ''
DEFAULT_GENDER = 'unknown'

MALE_GENDER_LIST = ['m', 'male', 'man', 'boy']
FEMALE_GENDER_LIST = ['f', 'female', 'woman', 'girl']

conn = None


########################################################################################################################
# MAIN FUNCTIONS
########################################################################################################################

def dicom2db(file_path, file_type, is_copy, step_id, db_conn):
    """
    Extract some meta-data from a DICOM file and store in a DB.
    :param file_path: File path.
    :param file_type: File type (should be 'DICOM').
    :param step_id: Step ID
    :param db_conn: Database connection.
    :return:
    """
    global conn
    conn = db_conn
    logging.info("Processing '%s'" % file_path)
    try:
        logging.info("Extracting DICOM headers from '%s'" % file_path)
        ds = dicom.read_file(file_path)
        participant_id = extract_participant(ds, DEFAULT_HANDEDNESS)
        scan_id = extract_scan(ds, participant_id, DEFAULT_ROLE, DEFAULT_COMMENT)
        session_id = extract_session(ds, scan_id)
        sequence_type_id = extract_sequence_type(ds)
        sequence_id = extract_sequence(session_id, sequence_type_id)
        repetition_id = extract_repetition(ds, sequence_id)
        extract_dicom(file_path, file_type, is_copy, repetition_id, step_id)
    except InvalidDicomError:
        logging.warning("%s is not a DICOM file !" % step_id)
    except IntegrityError:
        print_db_except()
        conn.db_session.rollback()


########################################################################################################################
# UTIL FUNCTIONS
########################################################################################################################

def format_date(date):
    try:
        return datetime.datetime(int(date[:4]), int(date[4:6]), int(date[6:8]))
    except ValueError:
        logging.warning("Cannot parse date "+str(date))


def format_gender(gender):
    if gender.lower() in MALE_GENDER_LIST:
        return 'male'
    elif gender.lower() in FEMALE_GENDER_LIST:
        return 'female'
    else:
        return 'unknown'


def print_db_except():
    logging.warning("A problem occurred while trying to insert data into DB.")
    logging.warning(
        "This can be caused by a duplicate entry on a unique field.")
    logging.warning("A rollback will be performed !")


########################################################################################################################
# EXTRACTION FUNCTION
########################################################################################################################


def extract_participant(ds, handedness):
    try:
        participant_id = ds.PatientID

        try:
            participant_birth_date = format_date(ds.PatientBirthDate)
        except AttributeError:
            logging.warning("Birth date is unknown")
            participant_birth_date = None
        try:
            participant_gender = format_gender(ds.PatientSex)
        except AttributeError:
            logging.warning("Gender is unknown")
            participant_gender = DEFAULT_GENDER

        participant = conn.db_session.query(
            conn.Participant).filter_by(id=participant_id).first()

        if not participant:
            participant = conn.Participant(
                id=participant_id,
                gender=participant_gender,
                handedness=handedness,
                birthdate=participant_birth_date
            )
            conn.db_session.add(participant)
            conn.db_session.commit()

        return participant.id
    except AttributeError:
        logging.warning("Cannot create participant because some of those fields are missing : "
                        "PatientID")


def extract_scan(ds, participant_id, role, comment):
    try:
        scan_date = format_date(ds.AcquisitionDate)
        if not scan_date:
            raise AttributeError
    except AttributeError:
        scan_date = format_date(ds.SeriesDate)  # If acquisition date is not available then we use the series date

    scan = conn.db_session.query(conn.Scan).filter_by(
        participant_id=participant_id, date=scan_date).first()

    if not scan:
        scan = conn.Scan(
            date=scan_date,
            role=role,
            comment=comment,
            participant_id=participant_id
        )
        conn.db_session.add(scan)
        conn.db_session.commit()

    return scan.id


def extract_session(ds, scan_id):
    try:
        session_value = str(ds.StudyID)

        session = conn.db_session.query(conn.Session).filter_by(
            scan_id=scan_id, value=session_value).first()

        if not session:
            session = conn.Session(
                scan_id=scan_id,
                value=session_value
            )
            conn.db_session.add(session)
            conn.db_session.commit()

        return session.id
    except AttributeError:
        logging.warning("Cannot create session because some of those fields are missing : "
                        "StudyID")


def extract_sequence_type(ds):
    try:
        sequence_name = ds.ProtocolName
    except AttributeError:
        logging.warning("Cannot create sequence_type because ProtocolName field is missing")
        sequence_name = 'unknown'
    try:
        manufacturer = ds.Manufacturer
    except AttributeError:
        logging.warning("Field Manufacturer does not exist")
        manufacturer = 'unknown'
    try:
        manufacturer_model_name = ds.ManufacturerModelName
    except AttributeError:
        logging.warning("Field ManufacturerModelName does not exist")
        manufacturer_model_name = 'unknown'
    try:
        institution_name = ds.InstitutionName
    except AttributeError:
        logging.warning("Field InstitutionName does not exist")
        institution_name = 'unknown'
    try:
        slice_thickness = float(ds.SliceThickness)
    except (AttributeError, ValueError):
        logging.warning("Field SliceThickness does not exist")
        slice_thickness = None
    try:
        repetition_time = float(ds.RepetitionTime)
    except (AttributeError, ValueError):
        logging.warning("Field RepetitionTime does not exist")
        repetition_time = None
    try:
        echo_time = float(ds.EchoTime)
    except (AttributeError, ValueError):
        logging.warning("Field EchoTime does not exist")
        echo_time = None
    try:
        number_of_phase_encoding_steps = int(ds.NumberOfPhaseEncodingSteps)
    except (AttributeError, ValueError):
        logging.warning("Field NumberOfPhaseEncodingSteps does not exist")
        number_of_phase_encoding_steps = None
    try:
        percent_phase_field_of_view = float(ds.PercentPhaseFieldOfView)
    except (AttributeError, ValueError):
        logging.warning("Field PercentPhaseFieldOfView does not exist")
        percent_phase_field_of_view = None
    try:
        pixel_bandwidth = int(ds.PixelBandwidth)
    except (AttributeError, ValueError):
        logging.warning("Field PixelBandwidth does not exist")
        pixel_bandwidth = None
    try:
        flip_angle = float(ds.FlipAngle)
    except (AttributeError, ValueError):
        logging.warning("Field FlipAngle does not exist")
        flip_angle = None
    try:
        rows = int(ds.Rows)
    except (AttributeError, ValueError):
        logging.warning("Field Rows does not exist")
        rows = None
    try:
        columns = int(ds.Columns)
    except (AttributeError, ValueError):
        logging.warning("Field Columns does not exist")
        columns = None
    try:
        magnetic_field_strength = float(ds.MagneticFieldStrength)
    except (AttributeError, ValueError):
        logging.warning("Field MagneticFieldStrength does not exist")
        magnetic_field_strength = None
    try:
        echo_train_length = int(ds.EchoTrainLength)
    except (AttributeError, ValueError):
        logging.warning("Field EchoTrainLength does not exist")
        echo_train_length = None
    try:
        percent_sampling = float(ds.PercentSampling)
    except (AttributeError, ValueError):
        logging.warning("Field PercentSampling does not exist")
        percent_sampling = None
    try:
        pixel_spacing = ds.PixelSpacing
    except AttributeError:
        logging.warning("Field PixelSpacing does not exist")
        pixel_spacing = None
    try:
        pixel_spacing_0 = float(pixel_spacing[0])
    except (AttributeError, ValueError):
        logging.warning("Field pixel_spacing0 does not exist")
        pixel_spacing_0 = None
    try:
        pixel_spacing_1 = float(pixel_spacing[1])
    except (AttributeError, ValueError):
        logging.warning("Field pixel_spacing1 does not exist")
        pixel_spacing_1 = None
    try:
        echo_number = int(ds.EchoNumber)
    except (AttributeError, ValueError):
        echo_number = None
    try:
        space_between_slices = float(ds[0x0018, 0x0088].value)
    except KeyError:
        space_between_slices = None

    sequence_type_list = conn.db_session.query(conn.SequenceType).filter_by(
        name=sequence_name,
        manufacturer=manufacturer,
        manufacturer_model_name=manufacturer_model_name,
        institution_name=institution_name,
        echo_number=echo_number,
        number_of_phase_encoding_steps=number_of_phase_encoding_steps,
        pixel_bandwidth=pixel_bandwidth,
        rows=rows,
        columns=columns,
        echo_train_length=echo_train_length
    ).all()

    sequence_type_list = list(filter(lambda s: not (
        str(s.slice_thickness) != str(slice_thickness)
        or str(s.repetition_time) != str(repetition_time)
        or str(s.echo_time) != str(echo_time)
        or str(s.percent_phase_field_of_view) != str(percent_phase_field_of_view)
        or str(s.flip_angle) != str(flip_angle)
        or str(s.magnetic_field_strength) != str(magnetic_field_strength)
        or str(s.flip_angle) != str(flip_angle)
        or str(s.percent_sampling) != str(percent_sampling)
        or str(s.pixel_spacing_0) != str(pixel_spacing_0)
        or str(s.pixel_spacing_1) != str(pixel_spacing_1)
    ), sequence_type_list))

    if len(sequence_type_list) > 0:
        sequence_type = sequence_type_list[0]
    else:
        sequence_type = conn.SequenceType(
            name=sequence_name,
            manufacturer=manufacturer,
            manufacturer_model_name=manufacturer_model_name,
            institution_name=institution_name,
            slice_thickness=slice_thickness,
            repetition_time=repetition_time,
            echo_time=echo_time,
            echo_number=echo_number,
            number_of_phase_encoding_steps=number_of_phase_encoding_steps,
            percent_phase_field_of_view=percent_phase_field_of_view,
            pixel_bandwidth=pixel_bandwidth,
            flip_angle=flip_angle,
            rows=rows,
            columns=columns,
            magnetic_field_strength=magnetic_field_strength,
            space_between_slices=space_between_slices,
            echo_train_length=echo_train_length,
            percent_sampling=percent_sampling,
            pixel_spacing_0=pixel_spacing_0,
            pixel_spacing_1=pixel_spacing_1
        )
        conn.db_session.add(sequence_type)
        conn.db_session.commit()

    return sequence_type.id


def extract_sequence(session_id, sequence_type_id):
    sequence = conn.db_session.query(conn.Sequence)\
        .filter_by(session_id=session_id, sequence_type_id=sequence_type_id)\
        .first()

    if not sequence:
        sequence = conn.Sequence(
            session_id=session_id,
            sequence_type_id=sequence_type_id
        )
        conn.db_session.add(sequence)
        conn.db_session.commit()

    return sequence.id


def extract_repetition(ds, sequence_id):
    try:
        repetition_value = int(ds.SeriesNumber)
        repetition = conn.db_session.query(conn.Repetition).filter_by(
            sequence_id=sequence_id, value=repetition_value).first()

        if not repetition:
            repetition = conn.Repetition(
                sequence_id=sequence_id,
                value=repetition_value
            )
            conn.db_session.add(repetition)
            conn.db_session.commit()

        return repetition.id
    except AttributeError:
        logging.warning("Cannot create repetition because some of those fields are missing : "
                        "SeriesNumber")


def extract_dicom(path, file_type, is_copy, repetition_id, processing_step_id):
    dcm = conn.db_session.query(conn.DataFile).filter_by(
        path=path, repetition_id=repetition_id).first()

    if not dcm:
        dcm = conn.DataFile(
            path=path,
            type=file_type,
            repetition_id=repetition_id,
            processing_step_id=processing_step_id,
            is_copy=is_copy
        )
        conn.db_session.add(dcm)
        conn.db_session.commit()

    return dcm.id
