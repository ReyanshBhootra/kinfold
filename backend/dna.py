"""Pedigree relationship and shared-cM consistency check.

Given recorded parent links, find how two people are related (closest common
ancestors) and whether an observed shared-cM amount fits that relationship's
reference range. This is a plausibility check on the recorded pedigree, not a
genetic likelihood or an identification.
"""
import json
from pathlib import Path

REFERENCE = json.loads((Path(__file__).resolve().parent.parent / "data" / "dna_reference.json").read_text(encoding="utf8"))
MAX_GENERATIONS = 5
GENOME_CM = 6970  # approx. cM-equivalent of relatedness 1.0 (parent/child, relatedness 0.5, average ~3485 cM)


def ancestors(person, parents, limit=MAX_GENERATIONS):
    """Shortest generation distance and the child below each ancestor: {ancestor: (generations, child)}."""
    found = {person: (0, None)}
    frontier = [person]
    for generation in range(1, limit + 1):
        following = []
        for child in frontier:
            for parent in sorted(parents.get(child, ())):
                if parent not in found:
                    found[parent] = (generation, child)
                    following.append(parent)
        frontier = following
    return found


def chain(person, ancestor, found):
    """(parent, child) links from an ancestor down to the person."""
    links, node = [], ancestor
    while node != person:
        child = found[node][1]
        links.append((node, child))
        node = child
    return links


def relationship_key(g1, g2, half):
    low, high = sorted((g1, g2))
    if low == 0:
        return {1: "parent_child", 2: "grandparent", 3: "great_grandparent"}.get(high)
    if (low, high) == (1, 1):
        return "half_sibling" if half else "full_sibling"
    if (low, high) == (1, 2):
        return "half_aunt_niece" if half else "aunt_niece"
    if half:
        return "half_1C" if (low, high) == (2, 2) else None
    if (low, high) == (1, 3):
        return "great_aunt_niece"
    if low == high:
        return f"{low - 1}C"
    if high - low == 1:
        return f"{low - 1}C1R"
    return None


def relationship(a, b, parents):
    """How a and b are related through recorded parent links, or None if no common ancestor is recorded."""
    if a == b:
        return None
    up_a, up_b = ancestors(a, parents), ancestors(b, parents)
    common = set(up_a) & set(up_b)
    if not common:
        return None
    best = min(up_a[x][0] + up_b[x][0] for x in common)
    closest = sorted(x for x in common if up_a[x][0] + up_b[x][0] == best)
    g1, g2 = up_a[closest[0]][0], up_b[closest[0]][0]
    shared = [x for x in closest if (up_a[x][0], up_b[x][0]) == (g1, g2)][:2]
    direct = g1 == 0 or g2 == 0
    half = not direct and len(shared) == 1
    relatedness = 2.0 ** -(g1 + g2) if direct else len(shared) * 2.0 ** -(g1 + g2)
    links = []
    for ancestor in shared:
        links += chain(a, ancestor, up_a) + chain(b, ancestor, up_b)
    return {"generations": (g1, g2), "half": half, "common_ancestors": shared, "relatedness": relatedness,
            "key": relationship_key(g1, g2, half), "links": sorted(set(links))}


def describe(related):
    g1, g2 = related["generations"]
    return f"{'half-' if related['half'] else ''}relatives {g1} and {g2} generations below a recorded common ancestor"


def check(observed_cm, related):
    """consistent / inconsistent / unchecked for an observed amount and a relationship (or None)."""
    if related is None:
        return {"status": "unchecked", "reason": "no_recorded_common_ancestor", "observed_cm": observed_cm}
    reference = REFERENCE["relationships"].get(related["key"] or "")
    base = {"observed_cm": observed_cm, "relationship_key": related["key"], "theoretical_average_cm": round(GENOME_CM * related["relatedness"])}
    if reference is None:
        return {**base, "status": "unchecked", "reason": "no_reference_range", "relationship_label": describe(related)}
    status = "consistent" if reference["low_cM"] <= observed_cm <= reference["high_cM"] else "inconsistent"
    return {**base, "status": status, "relationship_label": reference["label"], "expected_low_cm": reference["low_cM"],
            "expected_high_cm": reference["high_cM"], "reference_source": reference["source"]}


def fitting_relationships(observed_cm):
    """Reference relationships whose range contains the observed amount, closest first."""
    order = ["parent_child", "full_sibling", "half_sibling", "grandparent", "aunt_niece", "half_aunt_niece", "great_grandparent",
             "great_aunt_niece", "1C", "half_1C", "1C1R", "2C", "2C1R", "3C"]
    table = REFERENCE["relationships"]
    return [table[k]["label"] for k in order if table[k]["low_cM"] <= observed_cm <= table[k]["high_cM"]]
