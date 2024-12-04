import json
import logging

from jinja2 import BaseLoader, TemplateNotFound
from google.cloud import storage
import os
import jinja2 as j2

from prompt_poet import TemplateLoader


logger = logging.getLogger(__name__)


class GCSLoader(BaseLoader):
    def __init__(self, bucket_name: str, client: storage.Client, local_dir: str, prefix: str = '', ):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.client = client
        self.bucket = self.client.bucket(bucket_name)
        self._local_dir = local_dir
        os.makedirs(self._local_dir, exist_ok=True)
        self.generation_data = self._get_generation_data()

    def _get_generation_data(self) -> dict:
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
        return generation_data

    def _write_generation_data(self, generation_data: dict):
        local_generation_path = os.path.join(self._local_dir, ".generation")
        with open(local_generation_path, "w") as f:
            json.dump(generation_data, f)

    def get_source(self, environment, template):
        blob_name = os.path.join(self.prefix, template) if self.prefix else template
        blob = self.bucket.blob(blob_name)

        if not blob.exists():
            raise TemplateNotFound(template)

        source = blob.download_as_text()
        self.generation_data[template] = blob.generation
        self._write_generation_data(self.generation_data)

        def uptodate():
            latest_blob = self.bucket.blob(blob_name)
            latest_blob.reload()
            if latest_blob.generation != self.generation_data.get(template):
                return False
            return True
        return source, None, uptodate


class GCSCacheTemplateLoader(TemplateLoader):

    def __init__(self, bucket_name: str, template_path: str, gcs_client: storage.Client, local_dir: str):
        self._bucket_name = bucket_name
        self._gcs_client = gcs_client
        self._template_dir, self._template_name = _parse_template_path(template_path)
        self._local_dir = local_dir

    def load(self) -> j2.Template:
        try:
            loader = GCSLoader(bucket_name=self._bucket_name,
                               client=self._gcs_client,
                               local_dir=self._local_dir,
                               prefix=self._template_dir)
            env = j2.Environment(loader=loader)
            return env.get_template(self._template_name)
        except j2.TemplateNotFound as ex:
            raise j2.TemplateNotFound(
                f"Template not found: {ex} {self._template_dir} {self._template_name=} {self._bucket_name=}"
            )

    def id(self) -> str:
        return f"gcs://{self._bucket_name}/{self._template_dir}/{self._template_name}"


def _parse_template_path(template_path: str) -> tuple[str, str]:
    """Parse the template path to determine the template source."""
    template_dir, template_name = os.path.split(template_path)
    if not template_dir:
        template_dir = "."
    return template_dir, template_name


