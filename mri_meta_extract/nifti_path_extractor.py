class NiftiPathExtractor(object):
    """
    This is an abstract class. You should inherit from this class to implement a NIFTI path analyser for your dataset.
    """
    @staticmethod
    def extract_participant_id(file_path):
        raise NotImplementedError("You should implement extract_participant_id")

    @staticmethod
    def extract_scan_date(file_path):
        raise NotImplementedError("You should implement extract_scan_date")

    @staticmethod
    def extract_session(file_path):
        raise NotImplementedError("You should implement extract_participant_id")

    @staticmethod
    def extract_sequence(file_path):
        raise NotImplementedError("You should implement extract_session")

    @staticmethod
    def extract_repetition(file_path):
        raise NotImplementedError("You should implement extract_repetition")

    @staticmethod
    def extract_prefix_type(file_path):
        raise NotImplementedError("You should implement extract_prefix_type")

    @staticmethod
    def extract_postfix_type(file_path):
        raise NotImplementedError("You should implement extract_postfix_type")
