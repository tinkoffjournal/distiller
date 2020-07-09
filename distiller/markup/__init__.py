from types import ModuleType
from typing import Any, Callable, Dict, Iterable, Tuple, Type, Union

from ..base import BaseDistiller, DistillationResult, DistilledObject
from ..helpers import glue_multi_newlines
from ..nodes import Node
from .mapper import MapperConfig, NodeTypesMapper
from .parser import MarkupParser
from .preprocessor import compile_custom_tokens_patterns, tagify_custom_tokens

Preprocessor = Callable[[str], str]
Postprocessor = Callable[[Node], None]
CustomTagConfig = Union[Tuple[str, str, str], str]
DEFAULT_PREPROCESSORS = (glue_multi_newlines,)


class MarkupDistiller(BaseDistiller):
    types_mapper: NodeTypesMapper
    preprocessors: Tuple[Preprocessor, ...]
    postprocessors: Tuple[Postprocessor, ...]

    def __init__(
        self,
        rules: MapperConfig = None,
        types_module: ModuleType = None,
        return_type: Type['DistilledObject'] = None,
        include: Iterable[str] = None,
        exclude: Iterable[str] = None,
        preprocessors: Iterable[Preprocessor] = None,
        postprocessors: Iterable[Postprocessor] = None,
        tagify: CustomTagConfig = None,
    ):
        super().__init__(
            types_module=types_module, return_type=return_type, include=include, exclude=exclude
        )
        types_mapper = NodeTypesMapper.create(predefined_types=self.registry, rules=rules)
        for ruleset in types_mapper.tag_rules.values():
            for (_, cls) in ruleset:
                self.registry.add(cls)
        for (_, cls) in types_mapper.relations_rules:
            self.registry.add(cls)
        self.types_mapper = types_mapper
        self.preprocessors = tuple(preprocessors or ())
        if tagify:
            self.configure_custom_tags_parsing(tagify)
        self.preprocessors = DEFAULT_PREPROCESSORS + self.preprocessors
        self.postprocessors = tuple(postprocessors or ())

    def __call__(
        self, source: str, context: Dict[str, Any] = None, raise_validation_error: bool = False,
    ) -> DistillationResult:
        obj = self.return_type()
        markup = self.preprocess(source) if source else ''
        parser_instance = MarkupParser(
            markup,
            mapper=self.types_mapper,
            context={**self.context, **(context or {})},
            include=self.include,
            exclude=self.exclude,
            raise_validation_error=raise_validation_error,
            nodetasks=obj._State.tasks,
            postprocessors=self.postprocessors,
        )
        obj._State.parser = parser_instance
        obj.nodes = parser_instance.nodes
        return obj, parser_instance.errors

    def configure_custom_tags_parsing(self, config_: CustomTagConfig) -> None:
        config = config_ if isinstance(config_, tuple) else tuple(char for char in config_)
        assert len(config) == 3, 'Invalid tagification config'
        start_char, close_char, end_char = config
        patterns = compile_custom_tokens_patterns(start_char, close_char, end_char)

        def tagify(markup: str) -> str:
            return tagify_custom_tokens(markup, start_char, close_char, *patterns)

        self.preprocessors = (tagify,) + self.preprocessors

    def preprocess(self, markup: str) -> str:
        markup = markup.strip()
        for preprocessor_fn in self.preprocessors:
            markup = preprocessor_fn(markup)
        # TODO: escape square brackets with non-latin symbols inside
        return markup
