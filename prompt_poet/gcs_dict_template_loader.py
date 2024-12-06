import logging

from jinja2 import BaseLoader
from google.cloud import storage
import os
import jinja2 as j2

from template_loaders import parse_template_path, TemplateLoader

logger = logging.getLogger(__name__)


class CacheLoader(BaseLoader):
    """CacheLoader for Jinja2."""
    def __init__(self, mapping):
        self.mapping = mapping

    def get_source(self, environment, template):
        def uptodate():
            return True

        if template not in self.mapping:
            raise j2.TemplateNotFound(template)

        return self.mapping[template], template, uptodate


class GCSDictTemplateLoader(TemplateLoader):
    def __init__(self, bucket_name: str, template_path: str, gcs_client: storage.Client):
        self._bucket_name = bucket_name
        self._gcs_client = gcs_client
        self._template_dir, self._template_name = parse_template_path(template_path)
        self._mapping = {}
        self._generation_data = {}

    def _is_stale(self, blob: storage.Blob) -> bool:
        """Check if the file needs to be downloaded."""
        local_generation = self._generation_data.get(blob.name)
        return local_generation != blob.generation

    def _download(self):
        """Download all files from the specified GCS directory to the local cache."""
        bucket = self._gcs_client.bucket(self._bucket_name)
        blobs = bucket.list_blobs(prefix=self._template_dir)
        for blob in blobs:
            if blob.name.endswith("/"):
                continue
            if not is_yaml_jinja(blob.name):
                continue
            if not self._is_stale(blob):
                continue
            # Remove prefix and leading slash
            relative_path = os.path.relpath(blob.name, start=self._template_dir)
            source = blob.download_as_text()
            self._mapping[relative_path] = source
            self._generation_data[blob.name] = blob.generation

    def load(self) -> j2.Template:
        try:
            self._download()
            loader = CacheLoader(mapping=self._mapping)
            env = j2.Environment(loader=loader, auto_reload=False)
            template = env.get_template(self._template_name)
            return template
        except j2.TemplateNotFound as ex:
            raise j2.TemplateNotFound(
                f"Template not found: {ex} {self._template_name=} {self._template_dir=}"
            )
        except Exception as ex:
            raise Exception(f"Error while loading template: {ex} {self._template_name=} {self._template_dir=}")

    def id(self) -> str:
        return f"gcs://{self._bucket_name}/{self._template_dir}/{self._template_name}"


def is_yaml_jinja(filename):
    """
    Check if the given file is a YAML file processed with Jinja2.

    Args:
    filename (str): The name of the file to check.

    Returns:
    bool: True if the file ends with '.yml.j2', '.yaml.j2', '.yml.jinja2', or '.yaml.jinja2', False otherwise.
    """
    valid_extensions = ['.yml.j2', '.yaml.j2', '.yml.jinja2', '.yaml.jinja2']
    return any(filename.endswith(ext) for ext in valid_extensions)
