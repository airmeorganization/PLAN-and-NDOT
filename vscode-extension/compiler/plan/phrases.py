"""Phrase library for PLAN (spec/PLAN.md §8).

Phrases are built-in expression patterns that expand into Python and
add any needed standard library imports automatically.
"""
from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class PhraseDefinition:
    name: str
    auto_imports: List[str]
    description: str

PHRASE_REGISTRY = {
    'square_root': PhraseDefinition('square_root', ['math'], 'math.sqrt(x)'),
    'absolute_value': PhraseDefinition('absolute_value', [], 'abs(x)'),
    'length_of': PhraseDefinition('length_of', [], 'len(x)'),
    'sum_of': PhraseDefinition('sum_of', [], 'sum(x)'),
    'largest_of': PhraseDefinition('largest_of', [], 'max(x)'),
    'smallest_of': PhraseDefinition('smallest_of', [], 'min(x)'),
    'average_of': PhraseDefinition('average_of', ['statistics'], 'statistics.mean(x)'),
    'rounded': PhraseDefinition('rounded', [], 'round(x) / round(x, n)'),
    'as_text': PhraseDefinition('as_text', [], 'str(x)'),
    'as_number': PhraseDefinition('as_number', [], 'plan_rt.to_number(x)'),
    'as_whole_number': PhraseDefinition('as_whole_number', [], 'int(x)'),
    'uppercase': PhraseDefinition('uppercase', [], 'x.upper()'),
    'lowercase': PhraseDefinition('lowercase', [], 'x.lower()'),
    'sorted': PhraseDefinition('sorted', [], 'sorted(x)'),
    'reversed': PhraseDefinition('reversed', [], 'list(reversed(x))'),
    'split_by': PhraseDefinition('split_by', [], 'x.split(s)'),
    'joined_with': PhraseDefinition('joined_with', [], 's.join(str(i) for i in x)'),
    'random_number': PhraseDefinition('random_number', ['random'], 'random.randint(a, b)'),
    'random_item': PhraseDefinition('random_item', ['random'], 'random.choice(x)'),
    'current_time': PhraseDefinition('current_time', ['datetime'], 'datetime.datetime.now()'),
}
