"""Read private registration PDFs only after checking administrator access."""
from pathlib import PurePosixPath


def download_registration(client, storage_path, authorize):
    # Check on the server before every Storage read, including legacy clients.
    authorize()
    if not isinstance(storage_path, str):
        raise ValueError("Dokumentstien mangler.")
    parts = storage_path.split("/")
    if (not storage_path or "\\" in storage_path or ":" in storage_path
            or any(part in ("", ".", "..") for part in parts)
            or not storage_path.lower().endswith(".pdf")):
        raise ValueError("Dokumentstien skal pege på en PDF i gæsteregistreringer.")
    data = client.storage.from_("guest-registrations").download(storage_path)
    if not isinstance(data, bytes) or not data.startswith(b"%PDF-"):
        raise ValueError("Filen er ikke en gyldig PDF.")
    return PurePosixPath(storage_path).name, data
