from dataclasses import dataclass


@dataclass
class CanonicalInteraction:
    dataset_id: int
    pair_key: str
    interactor_a_ns: str
    interactor_a_id: str
    interactor_b_ns: str
    interactor_b_id: str
    interaction_type: str | None
    confidence_score: float | None
    publication_id: str | None
    source_file: str
    source_row: int
    parser_version: str


class RowValidationError(Exception):
    def __init__(self, row_no: int, code: str, message: str, raw_payload: str | None = None):
        super().__init__(message)
        self.row_no = row_no
        self.code = code
        self.message = message
        self.raw_payload = raw_payload
