import dicom  # pydicom
import datetime
import logging
import re

from sqlalchemy.exc import IntegrityError
from dicom.errors import InvalidDicomError  # pydicom.errors


########################################################################################################################
# GLOBAL VARIABLES
########################################################################################################################

conn = None


########################################################################################################################
# PUBLIC FUNCTIONS
########################################################################################################################

def dicom2db(file_path, file_type, is_copy, step_id, db_conn, sid_by_patient=False, pid_in_vid=False):
    """
    Extract some meta-data from a DICOM file and store in a DB.
    :param file_path: File path.
    :param file_type: File type (should be 'DICOM').
    :param is_copy: Indicate if this file is a copy.
    :param step_id: Step ID
    :param db_conn: Database connection.
    :param sid_by_patient: Rarely, a data set might use study IDs which are unique by patient (not for the whole study).
    E.g.: LREN data. In such a case, you have to enable this flag. This will use PatientID + StudyID as a session ID.
    :param pid_in_vid: Rarely, a data set might mix patient IDs and visit IDs. E.g. : LREN data. In such a case, you
    to enable this flag. This will try to split PatientID into VisitID and PatientID.
    :return: A dictionary containing the following IDs : participant_id, visit_id, session_id, sequence_type_id,
    sequence_id, repetition_id, file_id.
    """
    global conn
    conn = db_conn
    try:
        logging.info("Extracting DICOM headers from '%s'" % file_path)

        dcm = dicom.read_file(file_path)
        dataset = db_conn.get_dataset(step_id)

        participant_id = _extract_participant(dcm, dataset, pid_in_vid)
        visit_id = _extract_scan(dcm, dataset, participant_id, pid_in_vid)
        session_id = _extract_session(dcm, visit_id, sid_by_patient)
        sequence_type_id = _extract_sequence_type(dcm)
        sequence_id = _extract_sequence(session_id, sequence_type_id)
        repetition_id = _extract_repetition(dcm, sequence_id)
        file_id = extract_dicom(file_path, file_type, is_copy, repetition_id, step_id)
        return {'participant_id': participant_id, 'visit_id': visit_id, 'session_id': session_id,
                'sequence_type_id': sequence_type_id, 'sequence_id': sequence_id, 'repetition_id': repetition_id,
                'file_id': file_id}
    except InvalidDicomError:
        logging.warning("%s is not a DICOM file !" % step_id)
    except IntegrityError:
        logging.warning("A problem occurred with the DB ! A rollback will be performed...")
        conn.db_session.rollback()


def extract_dicom(path, file_type, is_copy, repetition_id, processing_step_id):
    df = conn.db_session.query(conn.DataFile).filter_by(path=path).one_or_none()

    if not df:
        df = conn.DataFile(
            path=path,
            type=file_type,
            repetition_id=repetition_id,
            processing_step_id=processing_step_id,
            is_copy=is_copy
        )
        conn.db_session.add(df)
    else:
        df.file_type = file_type
        df.repetition_id = repetition_id
        df.processing_step_id = processing_step_id
        df.is_copy = is_copy
    conn.db_session.commit()

    return df.id


########################################################################################################################
# PRIVATE UTIL FUNCTIONS
########################################################################################################################

def _format_date(date):
    try:
        return datetime.datetime(int(date[:4]), int(date[4:6]), int(date[6:8]))
    except ValueError:
        logging.warning("Cannot parse date from : "+str(date))


def _format_age(age):
    try:
        unit = age[3].upper()
        value = int(age[:3])
        if "Y" == unit:
            return float(value)
        elif "M" == unit:
            return float(value/12)
        elif "W" == unit:
            return float(value/52.1429)
        elif "D" == unit:
            return float(value/365)
        else:
            raise ValueError
    except ValueError:
        logging.warning("Cannot parse age from : "+str(age))


def _split_patient_id(participant_id):
    res = re.split("_", participant_id)
    if len(res) == 2:
        return res


########################################################################################################################
# PRIVATE EXTRACTION FUNCTION
########################################################################################################################


def _extract_participant(dcm, dataset, pid_in_vid=False):
    try:
        participant_id = dcm.PatientID
        if pid_in_vid:
            try:
                participant_id = _split_patient_id(participant_id)[1]
            except TypeError:
                pass

    except AttributeError:
        logging.warning("Patient ID was not found !")
        participant_id = None
    try:
        participant_birth_date = _format_date(dcm.PatientBirthDate)
    except AttributeError:
        logging.debug("Field PatientBirthDate was not found")
        participant_birth_date = None
    try:
        participant_age = _format_age(dcm.PatientAge)
    except AttributeError:
        logging.debug("Field PatientAge was not found")
        participant_age = None
    try:
        participant_gender = dcm.PatientSex
    except AttributeError:
        logging.debug("Field PatientSex was not found")
        participant_gender = None

    participant_id = conn.get_participant_id(participant_id, dataset)

    participant = conn.db_session.query(
        conn.Participant).filter_by(id=participant_id).one_or_none()

    if not participant:
        participant = conn.Participant(
            id=participant_id,
            gender=participant_gender,
            birth_date=participant_birth_date,
            age=participant_age,
        )
        conn.db_session.add(participant)
    else:
        participant.gender = participant_gender
        participant.birth_date = participant_birth_date
        participant.age = participant_age
    conn.db_session.commit()

    return participant.id


def _extract_scan(dcm, dataset, participant_id, by_patient=False, pid_in_vid=False):
    try:
        scan_date = _format_date(dcm.AcquisitionDate)
        if not scan_date:
            raise AttributeError
    except AttributeError:
        scan_date = _format_date(dcm.SeriesDate)  # If acquisition date is not available then we use the series date

    visit_id = None
    if pid_in_vid:
        try:
            patient_id = dcm.PatientID
            if pid_in_vid:
                visit_id = _split_patient_id(patient_id)[0]
        except AttributeError:
            logging.warning("Patient ID was not found !")
            visit_id = None
    if not pid_in_vid or not visit_id:
        try:
            visit_id = str(dcm.StudyID)
            if by_patient:
                visit_id += str(dcm.PatientID)
        except AttributeError:
            logging.debug("Field StudyID was not found")
            visit_id = None

    visit_id = conn.get_visit_id(visit_id, dataset)

    visit = conn.db_session.query(conn.Visit).filter_by(id=visit_id).one_or_none()

    if not visit:
        visit = conn.Visit(
            id=visit_id,
            date=scan_date,
            participant_id=participant_id,
        )
        conn.db_session.add(visit)
    else:
        visit.date = scan_date
        visit.participant_id = participant_id
    conn.db_session.commit()

    return visit.id


def _extract_session(dcm, visit_id, by_patient=False):
    try:
        session_value = str(dcm.StudyID)
        if by_patient:
            session_value += str(dcm.PatientID)
    except AttributeError:
        logging.debug("Field StudyID was not found")
        session_value = None

    session = conn.db_session.query(conn.Session).filter_by(
        visit_id=visit_id, name=session_value).first()

    if not session:
        session = conn.Session(
            visit_id=visit_id,
            name=session_value,
        )
        conn.db_session.add(session)
        conn.db_session.commit()

    return session.id


def _extract_sequence_type(dcm):
    try:
        sequence_name = dcm.SeriesDescription  # It seems better to use this instead of ProtocolName
    except AttributeError:
        logging.debug("Field SeriesDescription was not found")
        try:
            sequence_name = dcm.ProtocolName  # It seems better to use this instead of SeriesDescription
        except AttributeError:
            sequence_name = None
    try:
        manufacturer = dcm.Manufacturer
    except AttributeError:
        logging.debug("Field Manufacturer was not found")
        manufacturer = None
    try:
        manufacturer_model_name = dcm.ManufacturerModelName
    except AttributeError:
        logging.debug("Field ManufacturerModelName was not found")
        manufacturer_model_name = None
    try:
        institution_name = dcm.InstitutionName
    except AttributeError:
        logging.debug("Field InstitutionName was not found")
        institution_name = None
    try:
        slice_thickness = float(dcm.SliceThickness)
    except (AttributeError, ValueError):
        logging.debug("Field SliceThickness was not found")
        slice_thickness = None
    try:
        repetition_time = float(dcm.RepetitionTime)
    except (AttributeError, ValueError):
        logging.debug("Field RepetitionTime was not found")
        repetition_time = None
    try:
        echo_time = float(dcm.EchoTime)
    except (AttributeError, ValueError):
        logging.debug("Field EchoTime was not found")
        echo_time = None
    try:
        number_of_phase_encoding_steps = int(dcm.NumberOfPhaseEncodingSteps)
    except (AttributeError, ValueError):
        logging.debug("Field NumberOfPhaseEncodingSteps was not found")
        number_of_phase_encoding_steps = None
    try:
        percent_phase_field_of_view = float(dcm.PercentPhaseFieldOfView)
    except (AttributeError, ValueError):
        logging.debug("Field PercentPhaseFieldOfView was not found")
        percent_phase_field_of_view = None
    try:
        pixel_bandwidth = int(dcm.PixelBandwidth)
    except (AttributeError, ValueError):
        logging.debug("Field PixelBandwidth was not found")
        pixel_bandwidth = None
    try:
        flip_angle = float(dcm.FlipAngle)
    except (AttributeError, ValueError):
        logging.debug("Field FlipAngle was not found")
        flip_angle = None
    try:
        rows = int(dcm.Rows)
    except (AttributeError, ValueError):
        logging.debug("Field Rows was not found")
        rows = None
    try:
        columns = int(dcm.Columns)
    except (AttributeError, ValueError):
        logging.debug("Field Columns was not found")
        columns = None
    try:
        magnetic_field_strength = float(dcm.MagneticFieldStrength)
    except (AttributeError, ValueError):
        logging.debug("Field MagneticFieldStrength was not found")
        magnetic_field_strength = None
    try:
        echo_train_length = int(dcm.EchoTrainLength)
    except (AttributeError, ValueError):
        logging.debug("Field EchoTrainLength was not found")
        echo_train_length = None
    try:
        percent_sampling = float(dcm.PercentSampling)
    except (AttributeError, ValueError):
        logging.debug("Field PercentSampling was not found")
        percent_sampling = None
    try:
        pixel_spacing = dcm.PixelSpacing
    except AttributeError:
        logging.debug("Field PixelSpacing was not found")
        pixel_spacing = None
    try:
        pixel_spacing_0 = float(pixel_spacing[0])
    except (AttributeError, ValueError, TypeError):
        logging.debug("Field pixel_spacing0 was not found")
        pixel_spacing_0 = None
    try:
        pixel_spacing_1 = float(pixel_spacing[1])
    except (AttributeError, ValueError, TypeError):
        logging.debug("Field pixel_spacing1 was not found")
        pixel_spacing_1 = None
    try:
        echo_number = int(dcm.EchoNumber)
    except (AttributeError, ValueError):
        logging.debug("Field echo_number was not found")
        echo_number = None
    try:
        space_between_slices = float(dcm[0x0018, 0x0088].value)
    except (AttributeError, ValueError, KeyError):
        logging.debug("Field space_between_slices was not found")
        space_between_slices = None

    sequence_type_list = conn.db_session.query(conn.SequenceType).filter_by(
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
    ).all()

    sequence_type_list = list(filter(lambda s: not (
        str(s.name) != str(sequence_name)
        or str(s.manufacturer) != str(manufacturer)
        or str(s.manufacturer_model_name) != str(manufacturer_model_name)
        or str(s.institution_name) != str(institution_name)
        or str(s.slice_thickness) != str(slice_thickness)
        or str(s.repetition_time) != str(repetition_time)
        or str(s.echo_time) != str(echo_time)
        or str(s.echo_number) != str(echo_number)
        or str(s.number_of_phase_encoding_steps) != str(number_of_phase_encoding_steps)
        or str(s.percent_phase_field_of_view) != str(percent_phase_field_of_view)
        or str(s.pixel_bandwidth) != str(pixel_bandwidth)
        or str(s.flip_angle) != str(flip_angle)
        or str(s.rows) != str(rows)
        or str(s.columns) != str(columns)
        or str(s.magnetic_field_strength) != str(magnetic_field_strength)
        or str(s.space_between_slices) != str(space_between_slices)
        or str(s.echo_train_length) != str(echo_train_length)
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


def _extract_sequence(session_id, sequence_type_id):
    name = conn.db_session.query(conn.SequenceType).filter_by(id=sequence_type_id).one_or_none().name
    sequence = conn.db_session.query(conn.Sequence).filter_by(session_id=session_id, name=name).one_or_none()

    if not sequence:
        sequence = conn.Sequence(
            name=name,
            session_id=session_id,
            sequence_type_id=sequence_type_id,
        )
        conn.db_session.add(sequence)

    else:
        sequence.sequence_type_id = sequence_type_id
    conn.db_session.commit()

    return sequence.id


def _extract_repetition(dcm, sequence_id):
    try:
        repetition_name = str(dcm.SeriesNumber)
    except AttributeError:
        logging.warning("Field SeriesNumber was not found")
        repetition_name = None
    try:
        series_date = _format_date(dcm.SeriesDate)
        if not series_date:
            raise AttributeError
    except AttributeError:
        series_date = None

    repetition = conn.db_session.query(conn.Repetition).filter_by(
        sequence_id=sequence_id, name=repetition_name).one_or_none()

    if not repetition:
        repetition = conn.Repetition(
            sequence_id=sequence_id,
            name=repetition_name,
            date=series_date
        )
        conn.db_session.add(repetition)
    else:
        repetition.date = series_date
    conn.db_session.commit()

    return repetition.id
