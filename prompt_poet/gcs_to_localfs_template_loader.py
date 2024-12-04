import json
import logging
from google.cloud import storage
import os
import jinja2 as j2

from prompt_poet import TemplateLoader, LocalFSTemplateLoader


logger = logging.getLogger(__name__)


def _parse_template_path(template_path: str) -> tuple[str, str]:
    """Parse the template path to determine the template source."""
    template_dir, template_name = os.path.split(template_path)
    if not template_dir:
        template_dir = "."
    return template_dir, template_name


class GCSToLocalFSTemplateLoader(TemplateLoader):

    def __init__(self, bucket_name: str, template_path: str, local_dir: str, gcs_client: storage.Client):
        self._bucket_name = bucket_name
        self._gcs_client = gcs_client
        self._template_dir, self._template_name = _parse_template_path(template_path)
        self._local_dir = local_dir
        # create the dir if not exist.
        os.makedirs(self._local_dir, exist_ok=True)

    @staticmethod
    def _should_download(generation_data, blob: storage.Blob) -> bool:
        """Check if the file needs to be downloaded."""
        local_generation = generation_data.get(blob.name)
        print(f"should i download {blob.name}?, local: {local_generation} - {str(blob.generation)}. so {local_generation != str(blob.generation)}")
        return local_generation != str(blob.generation)

    def _download(self):
        """Download all files from the specified GCS directory to the local directory."""
        bucket = self._gcs_client.bucket(self._bucket_name)
        blobs = bucket.list_blobs(prefix=self._template_dir)

        local_generation_path = os.path.join(self._local_dir, ".generation")
        try:
            # Read the cached generation data
            if os.path.exists(local_generation_path):
                with open(local_generation_path, "r") as f:
                    generation_data = json.load(f)
            else:
                generation_data = {}
        except Exception as e:
            logger.warning(f"Error checking generation: {e}")
            generation_data = {}

        for blob in blobs:
            if not self._should_download(generation_data, blob):
                continue

            relative_path = blob.name[len(self._template_dir) + 1:]  # Remove prefix and leading slash
            local_path = os.path.join(self._local_dir, relative_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            blob.download_to_filename(local_path)
            # Update the generation record
            generation_data[blob.name] = str(blob.generation)

        # Save the updated generation data
        local_generation_path = os.path.join(self._local_dir, ".generation")
        with open(local_generation_path, "w") as f:
            json.dump(generation_data, f)

    def load(self) -> j2.Template:
        try:
            self._download()
            local_template_path = os.path.join(self._local_dir, self._template_name)
            loader = LocalFSTemplateLoader(local_template_path)
            return loader.load()
        except j2.TemplateNotFound as ex:
            raise j2.TemplateNotFound(
                f"!!!! Template not found: {ex} {self._template_dir} {self._template_name=} {self._bucket_name=} {self._local_dir}"
            )

    def id(self) -> str:
        return f"gcs://{self._bucket_name}/{self._template_dir}/{self._template_name}"

