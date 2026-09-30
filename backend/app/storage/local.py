from pathlib import Path
import shutil

class LocalStorage:

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

        self.base_path.mkdir(
            parents=True,
            exist_ok=True
        )

    # ========================================================
    # CONVERT STORAGE KEY TO PATH
    # ========================================================

    def _path(
        self,
        key: str
    ) -> Path:

        path = Path(key)

        # If database already contains the
        # complete physical path, use it.

        if path.is_absolute():
            return path

        # If the key already starts with the
        # storage directory, don't duplicate it.

        try:

            if path.parts[0] == self.base_path.parts[-1]:
                return path

        except IndexError:
            pass

        return self.base_path / path

    # ========================================================
    # SAVE UPLOAD
    # ========================================================

    def save_upload(
        self,
        file_obj,
        destination_key: str
    ) -> tuple[str, int]:

        destination = self._path(
            destination_key
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        file_obj.seek(0)

        with destination.open("wb") as buffer:

            shutil.copyfileobj(
                file_obj,
                buffer
            )

        return (
            str(destination),
            destination.stat().st_size
        )

    # ========================================================
    # EXISTS
    # ========================================================

    def exists(
        self,
        key: str
    ) -> bool:

        path = self._path(key)

        return path.exists()

    # ========================================================
    # DELETE
    # ========================================================

    def delete(
        self,
        key: str
    ) -> None:

        path = self._path(key)

        if path.exists():

            path.unlink()

    # ========================================================
    # COPY
    # ========================================================

    def copy(
        self,
        source_key: str,
        destination_key: str
    ) -> tuple[str, int]:

        source = self._path(
            source_key
        )

        destination = self._path(
            destination_key
        )

        if not source.exists():

            raise FileNotFoundError(
                f"Source file does not exist: {source}"
            )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(
            source,
            destination
        )

        return (
            str(destination),
            destination.stat().st_size
        )

    # ========================================================
    # GET LOCAL PATH
    # ========================================================

    def get_path(
        self,
        key: str
    ) -> Path:

        return self._path(key)
