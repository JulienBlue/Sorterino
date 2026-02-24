from domain.document_metadata import DocumentMetadata
from usecases.rename_document import rename_document


class DummyDocument:
    def __init__(self, metadata):
        self.metadata = metadata


def test_lohnsteuer_rename():
    metadata = DocumentMetadata(
        year=2021,
        category="Steuer",
        document_type="Lohnsteuerbescheinigung",
        contexts={
            "Zeitraum": "09.08.-12.11.",
            "Firma": "Theater_Hagen_gGmbH"
        }
    )

    document = DummyDocument(metadata)

    filename = rename_document(document)

    assert filename == "09.08.-12.11._Theater_Hagen_gGmbH_Lohnsteuerbescheinigung.pdf"