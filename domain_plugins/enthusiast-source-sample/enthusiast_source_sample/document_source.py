import csv
from pathlib import Path

from enthusiast_ecommerce_common.interfaces import DocumentSourcePlugin
from enthusiast_ecommerce_common.structures import DocumentDetails


class SampleDocumentSource(DocumentSourcePlugin):
    TYPE = "sample-document"
    LABEL = "Sample Documents"

    def __init__(self):
        self.sample_file_path = Path(__file__).parent / "sample_documents.csv"

    def fetch(self) -> list[DocumentDetails]:
        results = []
        with open(self.sample_file_path, newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                results.append(DocumentDetails(url=row["URL"], title=row["Title"], content=row["Content"]))

        return results
