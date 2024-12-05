"""A Prompt Poet (PP) template registry."""

import logging
import threading
import time

import jinja2 as j2
from cachetools import TTLCache, LRUCache

from template_loaders import TemplateLoader

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
            background_update: bool = True,
    ):
        """Initialize template engine."""
        self._provided_logger = logger

        if not self._initialized or reset:
            if background_update:
                self._cache = LRUCache(maxsize=cache_max_size)
            else:
                self._cache = TTLCache(maxsize=cache_max_size, ttl=cache_ttl_secs)
            self._ttl = cache_ttl_secs
            self._default_template = None
            self._initialized = True
            self._last_update = None
            self._update_in_progress = False
            self._lock = threading.Lock()

    def _should_update(self):
        return self._last_update + self._ttl < time.time()

    def _load_internal(self, template_loader: TemplateLoader):
        """Load the template from GCS and update cache."""
        with self._lock:
            try:
                self._update_in_progress = True
                if not self._should_update():
                    return
                # Update the cached template and timestamp
                cache_key = template_loader.id()
                self._cache[cache_key] = template_loader.load()
                self._last_update = time.time()
            except Exception as ex:
                self.logger.error(f"Error loading template: {ex}")
            finally:
                self._update_in_progress = False

    def get_template(
            self,
            template_loader: TemplateLoader,
            use_cache: bool = False,
    ) -> j2.Template:
        """Get template from cache or load from disk.

        :param template_loader: A TemplateLoader instance that handles loading the template
            from its source.
        :param use_cache: Whether to use cached template if available. If False or the
            template is not in cache, it will be loaded from disk.
        :return: The loaded template
        """
        if not use_cache:
            return template_loader.load()

        cache_key = template_loader.id()
        if cache_key not in self._cache:
            self._cache[cache_key] = template_loader.load()
            self._last_update = time.time()

        if self._should_update() and not self._update_in_progress:
            threading.Thread(target=self._load_internal, args=(template_loader,), daemon=True).start()
        return self._cache[cache_key]

    @property
    def logger(self) -> str:
        """The logger to be used by this module."""
        if self._provided_logger:
            return self._provided_logger

        return logging.getLogger(__name__)
