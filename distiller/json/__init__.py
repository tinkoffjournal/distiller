from typing import Any, Dict

from ..base import BaseDistiller, DistillationResult


class JsonDistiller(BaseDistiller):
    def __call__(
        self,
        source: Dict[str, Any],
        context: Dict[str, Any] = None,
        raise_validation_error: bool = False,
    ) -> DistillationResult:
        raise NotImplementedError
