from .nifti_path_extractor import NiftiPathExtractor


class BIDSNiftiPathExtractor(NiftiPathExtractor):
    """
    TODO: implement the NiftiPathExtractor following the BIDS file structure
    """
    @staticmethod
    def extract_session(file_path):
        pass

    @staticmethod
    def extract_sequence(file_path):
        pass

    @staticmethod
    def extract_postfix_type(file_path):
        pass

    @staticmethod
    def extract_participant_id(file_path):
        pass

    @staticmethod
    def extract_scan_date(file_path):
        pass

    @staticmethod
    def extract_prefix_type(file_path):
        pass

    @staticmethod
    def extract_repetition(file_path):
        pass
