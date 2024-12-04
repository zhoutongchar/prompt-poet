"""A Prompt Poet (PP) template registry."""

import os
import jinja2 as j2

from abc import ABC, abstractmethod


class TemplateLoader(ABC):
    """Base class for template loaders.

    This abstract class defines the interface for loading templates from various sources.
    Concrete implementations should handle specific template loading scenarios like
    local filesystem, remote filesystem, etc.
    """
    @abstractmethod
    def load(self) -> j2.Template:
        """Load and return a Jinja2 template from the source."""
        pass

    @abstractmethod
    def id(self) -> str:
        """Generate a unique identifier for this template loader configuration."""
        pass


def _parse_template_path(template_path: str) -> tuple[str, str]:
    """Parse the template path to determine the template source."""
    template_dir, template_name = os.path.split(template_path)
    if not template_dir:
        template_dir = "."
    return template_dir, template_name


class LocalFSTemplateLoader(TemplateLoader):
    """Template loader for loading templates from the local filesystem."""

    def __init__(self, template_path: str):
        self._template_dir, self._template_name = _parse_template_path(template_path)

    def load(self) -> j2.Template:
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
        return f"file://{self._template_dir}/{self._template_name}"


class LocalPackageTemplateLoader(TemplateLoader):
    """Template loader for loading templates from Python packages."""
    def __init__(self, package_name: str, template_path: str):
        self._template_dir, self._template_name = _parse_template_path(template_path)
        self._package_name = package_name

    def load(self) -> j2.Template:
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

    def id(self):
        return f"file://{self._package_name}:{self._template_dir}/{self._template_name}"
