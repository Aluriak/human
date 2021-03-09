
import sys
import json
import random
import itertools
from collections import defaultdict
from concepts import Context
from enum import Enum


class Order(Enum):
    Random = 0
    LargestCoverFirst = 1
    LargestExtentFirst = 2
    LargestIntentFirst = 3
    LargestExtentOrIntentFirst = 4
    Minimized = 42


def auto_resume(objs, *, key_is_range:bool=False, value_is_range:bool=False, concept_order:Order=Order.LargestExtentOrIntentFirst):
    """
    objs -- map obj to the vars it possesses

    """
    objects, attributes = tuple(sorted(list(objs))), tuple(sorted(list(set(itertools.chain.from_iterable(objs.values())))))

    def gen_(concepts):
        for extent, intent in concepts:
            extent = format_list(extent, objects, key_is_range)
            intent = format_list(intent, attributes, value_is_range)
            yield extent, intent

    if concept_order is Order.Minimized:
        # try all orders, send only the best
        results = {order.name: tuple(extract_concepts_in_order(objs, order=order)) for order in Order if order is not concept_order}
        best = min(results, key=lambda o: len(results[o]))
        yield from gen_(results[best])
    else:
        yield from gen_(extract_concepts_in_order(objs, order=concept_order))

def format_list(values, all_values, is_range:bool) -> str:
    def gen_():
        fragments = tuple(fragmented_by(values, all_values))
        # if len(fragments) == 1:  # all values are here
            # yield 'all (' + f'{fragments[0][0]} to {fragments[0][-1]}' + ')'
            # return
        for fragment in fragments:
            if len(fragment) > 1:
                start, *_, stop = fragment
                if start == all_values[0]: start = f'first ({start})'
                if stop == all_values[-1]: stop = f'last ({stop})'
                yield f'from {start} to {stop}'
            else:
                # val = fragment[0]
                # if val == all_values[0]: val = f'start ({val})'
                # if val == all_values[-1]: val = f'stop ({val})'
                yield f'on {fragment[0]}'
    if is_range:
        elements = tuple(gen_())
    else:
        elements = tuple(ordered_by(values, all_values))
    if len(elements) > 1:
        return ', '.join(elements[:-1]) + ' and ' + elements[-1]
    elif len(elements) == 1:
        return elements[0]
    else:
        raise ValueError("Empty set of values sent to format_list(3) function.")


def fragmented_by(found:set, all_values:tuple) -> [(tuple)]:
    """Yield sublists of all_values containing only found elements

    >>> tuple(fragmented_by('ABDE', 'ABCDEF'))
    (('A', 'B'), ('D', 'E'))

    """
    current_set = []
    for val in all_values:
        if val in found:
            current_set.append(val)
        else:
            if current_set:
                yield current_set
            current_set = []
    if current_set:
        yield current_set

def ordered_by(found:set, all_values:tuple) -> tuple:
    """Yield list of found elements in the order given by all_values
    >>> tuple(fragmented_by('EDBA', 'ABCDEF'))
    ('A', 'B', 'D', 'E')
    """
    for val in all_values:
        if val in found:
            yield val


def extract_concepts_in_order(objs, order:Order) -> [(set, set)]:
    var_idx = list(set(itertools.chain.from_iterable(variables for variables in objs.values())))
    context_def = [
        [var_idx.index(variable) for variable in variables]
        for (obj, variables) in objs.items()
    ]
    ctx = Context.fromdict({'objects': list(objs), 'properties': var_idx, 'context': context_def})

    def linksof(c) -> set:
        "edges covered by the given concept"
        return set(itertools.product(c.extent, c.intent))

    concepts_cover = {c: linksof(c) for c in iter(ctx.lattice)}
    treated = set()  # set of edges already described

    def def_Random(concepts):
        return random.choice(tuple(concepts))
    def def_LargestCoverFirst(concepts):
        return max(concepts.keys(), key=lambda c: len(linksof(c) - treated))
    def def_LargestExtentFirst(concepts):
        return max(concepts.keys(), key=lambda c: len(c.extent))
    def def_LargestIntentFirst(concepts):
        return max(concepts.keys(), key=lambda c: len(c.intent))
    def def_LargestExtentOrIntentFirst(concepts):
        return max(concepts.keys(), key=lambda c: max(len(c.extent), len(c.intent)))

    while concepts_cover:
        best = locals()['def_' + order.name](concepts_cover)
        simplified_best = simplify_concept(best, treated)
        treated |= linksof(best)
        concepts_cover = {c: linksof(c) - treated for c in concepts_cover}
        concepts_cover = {c: links for c, links in concepts_cover.items() if len(links) > 0}
        if not simplified_best[0] or not simplified_best[1]: continue  # ignore the extremums
        yield simplified_best

def simplify_concept(concept:(set, set), covered_edges:set) -> (set, set):
    extent, intent = concept
    extent_edges = {
        obj: {(obj, attr) for attr in intent} - covered_edges
        for obj in extent
    }
    intent_edges = {
        attr: {(obj, attr) for obj in extent} - covered_edges
        for attr in intent
    }
    simplified_extent = {obj for obj, remaining_edges in extent_edges.items() if remaining_edges}
    simplified_intent = {att for att, remaining_edges in intent_edges.items() if remaining_edges}
    return simplified_extent, simplified_intent



if __name__ == '__main__':
    data = json.load(open(sys.argv[1]))
    # print(auto_resume({obj: defn['variables'] for obj, defn in data.items()}))

    # use two variables as the two sides of the table:
    d = defaultdict(list)
    for obj in data.values():
        vs = obj['variables']
        d[vs[0]].append(vs[1])
    for order in Order:
        solutions = tuple(auto_resume(d, key_is_range=True, concept_order=order))
        print(f'\n\n{len(solutions)} STEPS OF EXPLANATION WITH ORDER {order.name}:')
        for extent, intent in solutions:
            print('\t', extent, 'opening hours are:', intent)
            # print('\t', intent)
            print()
