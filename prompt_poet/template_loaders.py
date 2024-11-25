"""A Prompt Poet (PP) template registry."""

import os
import jinja2 as j2


class TemplateLoader:

    def load(self) -> j2.Template:
        pass

    def id(self) -> str:
        pass


def parse_template_path(template_path: str) -> tuple[str, str]:
    """Parse the template path to determine the template source."""
    template_dir, template_name = os.path.split(template_path)
    if not template_dir:
        template_dir = "."
    return template_dir, template_name


class LocalFSTemplateLoader(TemplateLoader):
    def __init__(self, template_path: str):
        self._template_dir, self._template_name = parse_template_path(template_path)

    def load(self) -> j2.Template:
        """Load template from disk."""
        try:
            loader = j2.FileSystemLoader(searchpath=self._template_dir)
        except j2.TemplateNotFound as ex:
            raise j2.TemplateNotFound(
                f"Template not found: {ex} {self._template_name=} {self._template_dir=}"
            )

        env = j2.Environment(loader=loader)
        template = env.get_template(self._template_name)
        return template

    def id(self):
        return f"{self._template_dir}/{self._template_name}"


class LocalPackageTemplateLoader(TemplateLoader):
    def __init__(self, package_name: str, template_path: str):
        self._template_dir, self._template_name = parse_template_path(template_path)
        self._package_name = package_name

    def load(self) -> j2.Template:
        """Load template from package on the disk."""
        try:
            loader = j2.PackageLoader(
                package_name=self._package_name, package_path=self._template_dir
            )
        except j2.TemplateNotFound as ex:
            raise j2.TemplateNotFound(
                f"Template not found: {ex} {self._template_name=} {self._template_dir=} {self._package_name=}"
            )
        env = j2.Environment(loader=loader)
        template = env.get_template(self._template_name)
        return template
