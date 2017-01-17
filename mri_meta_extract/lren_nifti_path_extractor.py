import re
from .nifti_path_extractor import NiftiPathExtractor


class LRENNiftiPathExtractor(NiftiPathExtractor):
    """
    Implementation of NiftiPathExtractor that follows the LREN folder structure.
    The LREN folder structure is as follow:
    ParticipantID/Session/Sequence/Repetition/image.nii (where the filename can contain a prefix and a postfix)
    """
    @staticmethod
    def extract_participant_id(file_path):
        return str(re.findall('/([^/]+?)/[^/]+?/[^/]+?/[^/]+?/[^/]+?\.nii', file_path)[0])

    @staticmethod
    def extract_scan_date(file_path):
        return None

    @staticmethod
    def extract_session(file_path):
        return str(re.findall('/([^/]+?)/[^/]+?/[^/]+?/[^/]+?\.nii', file_path)[0])

    @staticmethod
    def extract_sequence(file_path):
        return re.findall('/([^/]+?)/[^/]+?/[^/]+?\.nii', file_path)[0]

    @staticmethod
    def extract_repetition(file_path):
        return int(re.findall('/([^/]+?)/[^/]+?\.nii', file_path)[0])

    @staticmethod
    def extract_prefix_type(file_path):
        filename = re.findall('/([^/]+?)\.nii', file_path)[0]
        try:
            prefix_type = re.findall('(.*)PR', filename)[0]
        except IndexError:
            prefix_type = "unknown"
        return prefix_type

    @staticmethod
    def extract_postfix_type(file_path):
        filename = re.findall('/([^/]+?)\.nii', file_path)[0]
        try:
            postfix_type = re.findall('-\d\d_(.+)', filename)[0]
        except IndexError:
            postfix_type = "unknown"
        return postfix_type
