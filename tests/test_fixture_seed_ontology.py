"""Contract for `seed_upper_ontology.ttl` -- Project 5's frozen seed. Backs
the plan's I/O contract table golden invariant: "reasoner reports the
ontology + induced individuals CONSISTENT". These tests check the SEED
fixture itself is sound (parses, has the right shape, and its disjointness
axioms are genuinely load-bearing under OWL RL reasoning, not decorative
comments) -- reasoning over a real student's induced individuals is
Project 5's own job, not this fixture's.
"""
from pathlib import Path

import owlrl
import rdflib
from rdflib import OWL, RDF, RDFS, SKOS, Namespace

ONTOLOGY_PATH = Path(__file__).parent / "fixtures" / "corpus" / "seed_upper_ontology.ttl"
VNLP = Namespace("https://vietnlp.example/ontology#")

_UPPER_CLASSES = {
    "Entity", "Person", "Organization", "Place", "Event", "Artifact", "Concept", "TemporalEntity",
}


def _load() -> rdflib.Graph:
    g = rdflib.Graph()
    g.parse(ONTOLOGY_PATH, format="turtle")
    return g


def _reason(g: rdflib.Graph) -> list[str]:
    """Runs OWL RL forward-chaining and returns any inconsistency messages
    the reasoner reported (empty when the graph is consistent)."""
    reasoner = owlrl.OWLRL_Semantics(g, False, False)
    reasoner.closure()
    return reasoner.error_messages


def test_ontology_file_exists_and_parses_as_turtle():
    g = _load()
    assert len(g) > 0


def test_exactly_the_8_frozen_upper_classes_are_present():
    g = _load()
    classes = {str(c).rsplit("#", 1)[-1] for c in g.subjects(RDF.type, OWL.Class)}
    assert _UPPER_CLASSES <= classes


def test_between_15_and_20_domain_classes():
    g = _load()
    classes = {str(c).rsplit("#", 1)[-1] for c in g.subjects(RDF.type, OWL.Class)}
    domain_classes = classes - _UPPER_CLASSES
    assert 15 <= len(domain_classes) <= 20, domain_classes


def test_every_domain_class_attaches_under_a_frozen_upper_class():
    g = _load()
    classes = {c for c in g.subjects(RDF.type, OWL.Class)}
    upper_uris = {VNLP[name] for name in _UPPER_CLASSES}
    domain = classes - upper_uris
    for c in domain:
        parents = set(g.objects(c, RDFS.subClassOf))
        # walk up to a frozen upper class (domain hierarchy is at most 2 deep, e.g. City -> AdministrativeRegion -> Place)
        seen = set()
        frontier = parents
        reached_upper = False
        while frontier and not reached_upper:
            nxt = set()
            for p in frontier:
                if p in upper_uris:
                    reached_upper = True
                    break
                if p not in seen:
                    seen.add(p)
                    nxt |= set(g.objects(p, RDFS.subClassOf))
            frontier = nxt
        assert reached_upper, f"{c} does not attach under any frozen upper class"


def test_seed_ontology_alone_is_reasoner_consistent():
    assert _reason(_load()) == []


def test_disjointness_axioms_are_load_bearing_not_decorative():
    """A Person that is also asserted as an Organization must be flagged by
    the reasoner -- if this doesn't fire, the disjointness axioms in the
    file are dead weight, not an actual consistency check."""
    g = _load()
    g.add((VNLP.testIndividual, RDF.type, VNLP.Person))
    g.add((VNLP.testIndividual, RDF.type, VNLP.Organization))
    errors = _reason(g)
    assert errors, "disjointWith axioms did not fire under OWL RL reasoning"


def test_kinship_is_a_property_not_sibling_classes():
    """Per .claude/agents/ontology-engineer.md: anh/chi/em must be a
    property on Person, never sibling classes of Person."""
    g = _load()
    classes = {str(c).rsplit("#", 1)[-1].lower() for c in g.subjects(RDF.type, OWL.Class)}
    for banned in ("oldersibling", "youngersibling", "anh", "chi", "em"):
        assert banned not in classes
    assert (VNLP.kinshipRole, RDF.type, OWL.DatatypeProperty) in g
    assert (VNLP.kinshipRole, RDFS.domain, VNLP.Person) in g


def test_administrative_region_aligns_via_close_match_not_same_as():
    g = _load()
    assert list(g.objects(VNLP.AdministrativeRegion, SKOS.closeMatch))
    assert list(g.objects(VNLP.AdministrativeRegion, OWL.sameAs)) == []
