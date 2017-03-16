import logging
import re
from datetime import datetime


def format_date(date):
    try:
        return datetime(int(date[:4]), int(date[4:6]), int(date[6:8]))
    except ValueError:
        logging.warning("Cannot parse date from : "+str(date))


def format_age(age):
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


def split_patient_id(participant_id):
    res = re.split("_", participant_id)
    if len(res) == 2:
        return res
