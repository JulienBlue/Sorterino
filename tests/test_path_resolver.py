from usecases.path_resolver import PathResolver
from domain.document_metadata import DocumentMetadata


def test_bank_routing():
    structure = {
        "Finanzen": {
            "Banken": {
                "{Bank}": {
                    "Girokonto": {
                        "{Jahr}": {}
                    }
                }
            }
        }
    }

    resolver = PathResolver(structure)

    metadata = DocumentMetadata(
        year=2014,
        category="Finanzen",
        document_type="Kontoauszug",
        contexts={"Bank": "Deutsche_Bank"}
    )

    path = resolver.resolve(metadata)

    assert "Deutsche_Bank" in path
    assert "2014" in path