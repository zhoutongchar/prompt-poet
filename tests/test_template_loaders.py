from unittest.mock import Mock, patch

from google.cloud import storage
from template_loaders import GCSDictTemplateLoader
import jinja2 as j2


def test_gcs_dict_template_loader():
    # mock gcs storage.Client
    mock_client = Mock(spec=storage.Client)
    mock_bucket = Mock()
    mock_client.bucket.return_value = mock_bucket
    mock_blob = Mock()
    mock_blob.name = "test_templates/main_template.yml.j2"
    mock_blob.generation = 1234
    mock_blob.download_as_text.return_value = "template: This is a test template with {{ username }}."
    mock_bucket.list_blobs.return_value = [mock_blob]
    with patch('google.cloud.storage.Client', return_value=mock_client):
        loader = GCSDictTemplateLoader(
            bucket_name="test-bucket",
            template_path="test_templates/main_template.yml.j2",
            gcs_client=storage.Client()  # This will be the mock due to patching
        )
        template = loader.load()
        assert isinstance(template, j2.Template), "Should return a Jinja2 Template object."

        rendered = template.render(username="Jeff")
        assert "This is a test template with Jeff." in rendered

        assert loader.id() == "gcs://test-bucket/test_templates/main_template.yml.j2"
