from collections import defaultdict
from typing import Dict, Iterable, Mapping, NamedTuple, Set, Tuple

from bs4.element import Tag
from soupsieve import SoupSieve, compile as sv_compile

from ..nodes import Node, NodeType


class NodeTypesMapper(NamedTuple):
    tag_rules: 'MapperRules' = {}
    relations_rules: Set['MapperRule'] = set()
    default_node_type: NodeType = Node

    @classmethod
    def create(
        cls, predefined_types: Iterable[NodeType] = None, rules: 'MapperConfig' = None
    ) -> 'NodeTypesMapper':
        predefined_types = predefined_types or ()
        rules = rules or {}
        default_node_type = rules.pop('*', Node)
        tag_rules = defaultdict(list)
        relations_rules = set()

        for node_type in predefined_types:
            node_kind = node_type.get_node_kind_value()
            rule = sv_compile(pattern=node_kind)
            tag_rules[node_kind].append((rule, node_type))

        for pattern, node_type in rules.items():
            rule = sv_compile(pattern)
            compiled_mapper_rule = (rule, node_type)
            for selector in rule.selectors:
                if selector.relation:
                    relations_rules.add(compiled_mapper_rule)
                else:
                    tag_rules[selector.tag.name].append(compiled_mapper_rule)

        return cls(
            tag_rules=tag_rules,  # type: ignore
            relations_rules=relations_rules,
            default_node_type=default_node_type,
        )

    def find_tag_node_type(self, tag: Tag) -> NodeType:
        matched_node_type = None
        rules = self.tag_rules.get(tag.name) or self.tag_rules.get('*')
        for rule, node_type in rules or ():
            if rule.match(tag):
                matched_node_type = node_type
        return matched_node_type or self.default_node_type


CSSPattern = str
MapperConfig = Dict[CSSPattern, NodeType]
MapperRule = Tuple[SoupSieve, NodeType]
MapperRules = Mapping[str, Iterable[MapperRule]]
