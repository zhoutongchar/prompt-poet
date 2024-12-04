import json
import logging

from jinja2 import BaseLoader, TemplateNotFound
from google.cloud import storage
import os
import jinja2 as j2

from prompt_poet import TemplateLoader


logger = logging.getLogger(__name__)


class NaiveGCSLoader(BaseLoader):
    def __init__(self, bucket_name: str, client: storage.Client, prefix: str = ''):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.client = client
        self.bucket = self.client.bucket(bucket_name)

    def get_source(self, environment, template):
        blob_name = os.path.join(self.prefix, template) if self.prefix else template
        blob = self.bucket.blob(blob_name)

        if not blob.exists():
            raise TemplateNotFound(template)

        source = blob.download_as_text()

        def uptodate():
            # Always read from GCS and update the templates.
            return False

        return source, None, uptodate


class NaiveGCSTemplateLoader(TemplateLoader):

    def __init__(self, bucket_name: str, template_path: str, gcs_client: storage.Client):
        self._bucket_name = bucket_name
        self._gcs_client = gcs_client
        self._template_dir, self._template_name = _parse_template_path(template_path)

    def load(self) -> j2.Template:
        try:
            loader = NaiveGCSLoader(bucket_name=self._bucket_name, client=self._gcs_client, prefix=self._template_dir)
            env = j2.Environment(loader=loader)
            return env.get_template(self._template_name)
        except j2.TemplateNotFound as ex:
            raise j2.TemplateNotFound(
                f"!!!! Template not found: {ex} {self._template_dir} {self._template_name=} {self._bucket_name=}"
            )

    def id(self) -> str:
        return f"gcs://{self._bucket_name}/{self._template_dir}/{self._template_name}"


def _parse_template_path(template_path: str) -> tuple[str, str]:
    """Parse the template path to determine the template source."""
    template_dir, template_name = os.path.split(template_path)
    if not template_dir:
        template_dir = "."
    return template_dir, template_name


