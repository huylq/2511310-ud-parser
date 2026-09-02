"""Round-trip contract tests for `interfaces/`: every dataclass, once
built, must validate against its own module's schema/validator, and every
validator must actually reject a structurally broken object. These are
NOT a test of any project's real implementation (there isn't one yet) --
they exist to prove the contracts themselves are internally consistent
before any of the 9 student branches are cut from them.
"""
import pandera.errors
import pytest

from vietnlp.interfaces import export, linguistics, ner, ontology, oupm, semantics, serving, treebank, ud


def test_segmented_sentence_round_trip():
    sentence = linguistics.SegmentedSentence(
        sent_id="doc1:0",
        register="formal",
        tokens=(
            linguistics.Token(idx=0, form="Sinh viên", syllables=("Sinh", "viên"), upos="NOUN"),
            linguistics.Token(idx=1, form="học", syllables=("học",), upos="VERB"),
        ),
        source="stub",
    )
    assert linguistics.validate_segmented_sentence(sentence) is sentence


def test_segmented_sentence_rejects_zero_tokens():
    sentence = linguistics.SegmentedSentence(sent_id="doc1:0", register="formal", tokens=())
    with pytest.raises(ValueError):
        linguistics.validate_segmented_sentence(sentence)


def test_dependency_parse_round_trip_and_tree_shape():
    parse = ud.DependencyParse(
        sent_id="doc1:0",
        tokens=(
            ud.UDToken(idx=0, form="Sinh viên", upos="NOUN", head=2, deprel="nsubj"),
            ud.UDToken(idx=1, form="học", upos="VERB", head=0, deprel="root"),
        ),
        source="stub",
    )
    assert ud.validate_dependency_parse(parse) is parse
    assert ud.is_single_rooted_tree(parse)


def test_dependency_parse_rejects_two_roots():
    parse = ud.DependencyParse(
        sent_id="doc1:0",
        tokens=(
            ud.UDToken(idx=0, form="a", upos="NOUN", head=0, deprel="root"),
            ud.UDToken(idx=1, form="b", upos="VERB", head=0, deprel="root"),
        ),
    )
    ud.validate_dependency_parse(parse)  # per-row shape is fine
    assert not ud.is_single_rooted_tree(parse)  # tree-shape invariant is separate, and fails


def test_named_entities_round_trip():
    entities = [
        ner.NamedEntity(sent_id="doc1:0", token_start=0, token_end=1, label="PER", text="Nam", source="stub"),
    ]
    assert ner.validate_named_entities(entities) is entities


def test_named_entity_rejects_reversed_span():
    entities = [
        ner.NamedEntity(sent_id="doc1:0", token_start=2, token_end=1, label="PER", text="Nam", source="stub"),
    ]
    with pytest.raises(pandera.errors.SchemaError):
        ner.validate_named_entities(entities)


def test_coref_chain_round_trip():
    chain = ner.CorefChain(chain_id="c1", mention_ids=("doc1:0:0:1", "doc1:1:0:1"), source="stub")
    known = {"doc1:0:0:1", "doc1:1:0:1"}
    assert ner.validate_coref_chain(chain, known) is chain


def test_coref_chain_rejects_unknown_mention():
    chain = ner.CorefChain(chain_id="c1", mention_ids=("doc1:0:0:1", "doc1:9:0:1"), source="stub")
    with pytest.raises(ValueError):
        ner.validate_coref_chain(chain, known_mention_ids={"doc1:0:0:1"})


def test_adjudicated_sentence_round_trip():
    sentence = treebank.AdjudicatedSentence(
        sent_id="doc1:0",
        tokens=(ud.UDToken(idx=0, form="học", upos="VERB", head=0, deprel="root"),),
        decisions=(
            treebank.AdjudicationDecision(
                idx=0, field="upos", candidate_a="VERB", candidate_b="NOUN",
                decision="VERB", rationale="verb per predicate position, generalizes to all finite clauses",
            ),
        ),
        source="stub",
    )
    assert treebank.validate_adjudicated_sentence(sentence) is sentence


def test_adjudication_decision_requires_nonempty_rationale():
    sentence = treebank.AdjudicatedSentence(
        sent_id="doc1:0",
        tokens=(ud.UDToken(idx=0, form="học", upos="VERB", head=0, deprel="root"),),
        decisions=(
            treebank.AdjudicationDecision(
                idx=0, field="upos", candidate_a="VERB", candidate_b="NOUN", decision="VERB", rationale="",
            ),
        ),
    )
    with pytest.raises(pandera.errors.SchemaError):
        treebank.validate_adjudicated_sentence(sentence)


def test_ontology_individual_and_alignment_round_trip():
    individuals = [ontology.OntologyIndividual(entity_id="doc1:0:0:1", ontology_class="Person", source="stub")]
    assert ontology.validate_ontology_individuals(individuals) is individuals
    alignments = [
        ontology.AlignmentRecord(
            ontology_class="Place", external_uri="https://www.wikidata.org/wiki/Q1858",
            relation="skos:closeMatch", source="stub",
        )
    ]
    assert ontology.validate_alignment_records(alignments) is alignments


def test_alignment_record_rejects_unknown_relation():
    alignments = [
        ontology.AlignmentRecord(
            ontology_class="Place", external_uri="https://www.wikidata.org/wiki/Q1858",
            relation="owl:equivalentClass", source="stub",
        )
    ]
    with pytest.raises(pandera.errors.SchemaError):
        ontology.validate_alignment_records(alignments)


def test_logical_form_round_trip_and_balance_check():
    lf = semantics.LogicalForm(
        sent_id="doc1:0", form_sexp='(and (tok "học"))', predicates=('(tok "học")',), source="stub"
    )
    assert semantics.validate_logical_form(lf) is lf
    assert semantics.is_balanced("(a (b) c)")
    assert not semantics.is_balanced("(a (b)")


def test_logical_form_rejects_unbalanced_sexp():
    lf = semantics.LogicalForm(sent_id="doc1:0", form_sexp="(a (b)")
    with pytest.raises(ValueError):
        semantics.validate_logical_form(lf)


def test_entity_cluster_round_trip():
    cluster = oupm.EntityCluster(
        cluster_id="cl1", canonical_name="Nam", ontology_class="Person",
        mention_ids=("doc1:0:0:1",), posterior=0.9, source="stub",
    )
    assert oupm.validate_entity_cluster(cluster, known_mention_ids={"doc1:0:0:1"}) is cluster


def test_entity_cluster_rejects_posterior_out_of_range():
    cluster = oupm.EntityCluster(cluster_id="cl1", canonical_name="Nam", ontology_class=None, mention_ids=("m1",), posterior=1.5)
    with pytest.raises(ValueError):
        oupm.validate_entity_cluster(cluster)


def test_document_response_round_trip():
    doc = serving.DocumentResponse(
        id=1, content_hash="abc123", url=None, lang="vi", register="formal", quality_score=0.8,
        sentences=(serving.SentenceResponse(id=1, document_id=1, idx=0, text="Xin chào."),),
        entities=(
            serving.EntityResponse(
                id=1, canonical_name="Nam", ontology_class="Person", wikidata_qid=None, posterior=0.9
            ),
        ),
    )
    assert serving.validate_document_response(doc) is doc


def test_document_response_rejects_duplicate_sentence_idx():
    doc = serving.DocumentResponse(
        id=1, content_hash="abc123", url=None, lang="vi", register="formal", quality_score=0.8,
        sentences=(
            serving.SentenceResponse(id=1, document_id=1, idx=0, text="A."),
            serving.SentenceResponse(id=2, document_id=1, idx=0, text="B."),
        ),
    )
    with pytest.raises(ValueError):
        serving.validate_document_response(doc)


def test_export_row_and_benchmark_report_round_trip():
    rows = [
        export.ExportRow(sent_id="doc1:0", document_id="doc1", text="Xin chào.", register="formal", tokens=("Xin", "chào"))
    ]
    assert export.validate_export_rows(rows, expected_count=1) is rows
    report = export.validate_benchmark_report(
        export.BenchmarkReport(task="uit_vsfc", metric="f1", value=0.5, n_items=10, stub_note="format-shape stand-in only")
    )
    assert report.value == 0.5
    export.validate_dataset_card({"register_taxonomy", "normalization", "license", "known_limitations"})


def test_export_rows_rejects_row_count_mismatch():
    rows = [
        export.ExportRow(sent_id="doc1:0", document_id="doc1", text="Xin chào.", register="formal", tokens=("Xin", "chào"))
    ]
    with pytest.raises(ValueError):
        export.validate_export_rows(rows, expected_count=2)


def test_dataset_card_rejects_missing_section():
    with pytest.raises(ValueError):
        export.validate_dataset_card({"register_taxonomy", "license"})
