"""HTML/JSON documents parser into Pydantic models"""

__version__ = '0.1.0b4'

from pydantic import ValidationError

from .base import DistilledObject as Distilled, UnsupportedMarkupDistiller
from .nodes import InvalidNode, Node, NodeKind, TextNode

try:
    from .markup import MarkupDistiller
except ModuleNotFoundError:  # pragma: no cover
    MarkupDistiller = UnsupportedMarkupDistiller  # type: ignore


DistillerError = ValidationError

__all__ = (
    'MarkupDistiller',
    'Distilled',
    'DistillerError',
    'Node',
    'TextNode',
    'InvalidNode',
    'NodeKind',
)
