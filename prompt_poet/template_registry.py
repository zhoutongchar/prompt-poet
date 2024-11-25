"""A Prompt Poet (PP) template registry."""

import logging

import jinja2 as j2
from cachetools import TTLCache

from prompt_poet.template_loaders import TemplateLoader

CACHE_MAX_SIZE = 100
CACHE_TTL_SECS = 30


class TemplateRegistry:
    """A Prompt Poet (PP) template registry."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern that allows arbitrary arguments."""
        if cls._instance is None:
            cls._instance = super(TemplateRegistry, cls).__new__(cls)
            # Initialize _instance's attributes
            cls._instance._initialized = False

        return cls._instance

    def __init__(
            self,
            logger: logging.LoggerAdapter = None,
            reset: bool = False,
            cache_max_size: int = CACHE_MAX_SIZE,
            cache_ttl_secs: int = CACHE_TTL_SECS,
    ):
        """Initialize template engine."""
        self._provided_logger = logger

        if not self._initialized or reset:
            self._cache = TTLCache(maxsize=cache_max_size, ttl=cache_ttl_secs)
            self._default_template = None
            self._initialized = True

    def get_template(
            self,
            template_loader: TemplateLoader,
            use_cache: bool = False,
    ) -> j2.Template:
        """Get template from cache or load from disk.

        Args:
            template_loader: A TemplateLoader instance that handles loading the template
                from its source.
            use_cache: Whether to use cached template if available. If False or the
                template is not in cache, it will be loaded from disk.

        Returns:
            j2.Template: The loaded Jinja2 template object.
        """
        cache_key = template_loader.id()
        load_from_disk = not use_cache or cache_key not in self._cache

        if load_from_disk:
            self._cache[cache_key] = template_loader.load()

        return self._cache[cache_key]

    @property
    def logger(self) -> str:
        """The logger to be used by this module."""
        if self._provided_logger:
            return self._provided_logger

        return logging.getLogger(__name__)
