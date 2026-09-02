"""Stub-generator tests: every `interfaces.stubs.*` function must produce
output that (a) validates against its own module's schema/validator and
(b) is marked `source="stub"` -- the provenance flag the gate's step 4
checks for every REAL submission (a stub must always carry this value,
never `"real"`).
"""
from vietnlp.interfaces import linguistics, ner, ontology, oupm, semantics, treebank, ud
from vietnlp.interfaces.stubs import (
    linguistics_stub,
    ner_stub,
    ontology_stub,
    oupm_stub,
    semantics_stub,
    treebank_stub,
    ud_stub,
)


def _stub_sentence(text="Sinh viên học bài ."):
    return linguistics_stub.stub_segment("doc1:0", "formal", text)


def test_linguistics_stub_round_trip():
    sentence = _stub_sentence()
    assert sentence.source == "stub"
    assert linguistics.validate_segmented_sentence(sentence) is sentence
    # naive: splits on whitespace, never merges syllables into one word
    assert [t.form for t in sentence.tokens] == ["Sinh", "viên", "học", "bài", "."]
    assert all(t.upos == "X" for t in sentence.tokens)


def test_ud_stub_round_trip():
    parse = ud_stub.stub_parse(_stub_sentence())
    assert parse.source == "stub"
    assert ud.validate_dependency_parse(parse) is parse
    assert ud.is_single_rooted_tree(parse)


def test_ner_stub_round_trip():
    sentence = _stub_sentence("Nam gặp Nam .")
    entities = ner_stub.stub_extract_entities(sentence)
    assert entities  # "Nam" appears twice, both capitalized
    assert all(e.source == "stub" for e in entities)
    assert ner.validate_named_entities(entities) is entities

    chains = ner_stub.stub_coref(entities)
    assert len(chains) == 1  # the two "Nam" spans exact-match on text
    assert chains[0].source == "stub"
    known = {e.mention_id for e in entities}
    assert ner.validate_coref_chain(chains[0], known) is chains[0]


def test_ner_stub_produces_no_chain_for_singletons():
    sentence = _stub_sentence("Nam học bài .")
    entities = ner_stub.stub_extract_entities(sentence)
    assert len(entities) == 1
    assert ner_stub.stub_coref(entities) == []


def test_treebank_stub_round_trip():
    parse = ud_stub.stub_parse(_stub_sentence())
    other = ud.DependencyParse(
        sent_id=parse.sent_id,
        tokens=tuple(
            ud.UDToken(idx=t.idx, form=t.form, upos="NOUN", head=t.head, deprel=t.deprel) for t in parse.tokens
        ),
    )
    adjudicated = treebank_stub.stub_adjudicate(parse.sent_id, parse.tokens, other.tokens)
    assert adjudicated.source == "stub"
    assert adjudicated.decisions  # every token's upos disagrees (stub tags "X", other tags "NOUN")
    assert treebank.validate_adjudicated_sentence(adjudicated) is adjudicated


def test_treebank_stub_rejects_mismatched_system_lengths():
    parse = ud_stub.stub_parse(_stub_sentence())
    try:
        treebank_stub.stub_adjudicate(parse.sent_id, parse.tokens, parse.tokens[:-1])
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_ontology_stub_round_trip():
    entity = ner.NamedEntity(sent_id="doc1:0", token_start=0, token_end=1, label="PER", text="Nam", source="stub")
    individual = ontology_stub.stub_individual(entity)
    assert individual.source == "stub"
    assert individual.ontology_class == "Person"
    assert ontology.validate_ontology_individuals([individual]) == [individual]


def test_semantics_stub_round_trip():
    parse = ud_stub.stub_parse(_stub_sentence())
    lf = semantics_stub.stub_logical_form(parse)
    assert lf.source == "stub"
    assert semantics.validate_logical_form(lf) is lf
    assert lf.type_checked is False


def test_oupm_stub_round_trip():
    sentence = _stub_sentence("Nam gặp Nam .")
    entities = ner_stub.stub_extract_entities(sentence)
    chains = ner_stub.stub_coref(entities)
    clusters = oupm_stub.stub_cluster(entities, chains)
    assert clusters
    assert all(c.source == "stub" for c in clusters)
    known = {e.mention_id for e in entities}
    for cluster in clusters:
        assert oupm.validate_entity_cluster(cluster, known_mention_ids=known) is cluster


def test_oupm_stub_singleton_entity_gets_its_own_cluster():
    sentence = _stub_sentence("Nam học bài .")
    entities = ner_stub.stub_extract_entities(sentence)
    clusters = oupm_stub.stub_cluster(entities, chains=[])
    assert len(clusters) == 1
    assert clusters[0].mention_ids == (entities[0].mention_id,)
    assert clusters[0].canonical_name == "Nam"
