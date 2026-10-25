"""CoNLL-U input, label mapping and projection for dependency parsing."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from vietnlp.interfaces._common import UD_DEPREL


PROJECTION_VERSION = "v2-first-dep-directional-glue"


VTB_LABEL_MAPPING = {
    label: label.partition(":")[0]
    for label in """
    acl acl:relcl acl:subj acl:tmod acl:tonp advcl advcl:objective advmod advmod:adj
    advmod:dir advmod:neg amod appos appos:nmod aux aux:pass case cc ccomp clf clf:det
    compound compound:adj compound:amod compound:apr compound:atov compound:dir
    compound:pron compound:prt compound:redup compound:svc compound:verbnoun
    compound:vmod compound:z conj cop csubj csubj:asubj csubj:pass csubj:vsubj dep det
    det:pmod discourse dislocated expl fixed flat flat:date flat:foreign flat:name
    flat:number flat:redup flat:time iobj list mark mark:pcomp nmod nmod:poss nsubj
    nsubj:nn nsubj:pass nsubj:xsubj nummod nummod:det obj obl obl:about obl:adj obl:adv
    obl:agent obl:comp obl:iobj obl:tmod obl:with parataxis punct root vocative xcomp
    xcomp:adj xcomp:dir xcomp:vcomp
    """.split()
}


def map_deprel(label: str) -> str:
    """Map known VTB labels to base labels; reject unknown labels."""
    if label in UD_DEPREL:
        return label
    try:
        return VTB_LABEL_MAPPING[label]
    except KeyError as exc:
        raise ValueError(f"Unknown dependency label: {label!r}") from exc


@dataclass(frozen=True)
class ConlluToken:
    id: int
    form: str
    upos: str
    head: int
    deprel: str
    line_number: int


@dataclass(frozen=True)
class ConlluSentence:
    metadata: dict[str, str]
    tokens: tuple[ConlluToken, ...]


@dataclass(frozen=True)
class ProjectedSentence:
    metadata: dict[str, str]
    tokens: tuple[ConlluToken, ...]
    word_to_syllables: dict[int, tuple[int, ...]]
    syllable_to_word: dict[int, int]
    is_projective: bool


def _validate_conllu_tree(tokens: list[ConlluToken]) -> None:
    for token in tokens:
        if not 0 <= token.head <= len(tokens):
            raise ValueError(
                f"CoNLL-U line {token.line_number}: HEAD is outside the sentence"
            )
        if (token.head == 0) != (token.deprel == "root"):
            raise ValueError(
                f"CoNLL-U line {token.line_number}: HEAD=0 requires DEPREL=root and vice versa"
            )

    if sum(token.head == 0 for token in tokens) != 1:
        raise ValueError(
            f"CoNLL-U line {tokens[0].line_number}: expected exactly one root"
        )

    completed = {0}
    for token in tokens:
        path: set[int] = set()
        current = token.id
        while current not in completed:
            if current in path:
                raise ValueError(
                    f"CoNLL-U line {tokens[current - 1].line_number}: dependency cycle"
                )
            path.add(current)
            current = tokens[current - 1].head
        completed.update(path)


def read_conllu(text: str) -> list[ConlluSentence]:
    """Read integer-ID basic trees, retaining metadata and source annotations."""
    sentences: list[ConlluSentence] = []
    metadata: dict[str, str] = {}
    tokens: list[ConlluToken] = []

    # A final separator flushes the last sentence even without a trailing newline.
    for line_number, line in enumerate(text.splitlines() + [""], start=1):
        if not line.strip():
            if tokens:
                _validate_conllu_tree(tokens)
                sentences.append(ConlluSentence(metadata, tuple(tokens)))
            metadata, tokens = {}, []
            continue

        if line.startswith("#"):
            key, separator, value = line[1:].partition("=")
            if separator:
                metadata[key.strip()] = value.strip()
            continue

        fields = line.split("\t")
        if len(fields) != 10:
            raise ValueError(
                f"CoNLL-U line {line_number}: expected 10 TAB-separated columns"
            )

        if re.fullmatch(r"[1-9][0-9]*(?:-[1-9][0-9]*|\.[1-9][0-9]*)", fields[0]):
            continue

        try:
            token_id = int(fields[0])
        except ValueError as exc:
            raise ValueError(
                f"CoNLL-U line {line_number}: ID must be an integer"
            ) from exc
        if token_id != len(tokens) + 1:
            raise ValueError(
                f"CoNLL-U line {line_number}: IDs must be consecutive from 1"
            )

        try:
            head = int(fields[6])
        except ValueError as exc:
            raise ValueError(
                f"CoNLL-U line {line_number}: HEAD must be an integer"
            ) from exc

        tokens.append(
            ConlluToken(
                id=token_id,
                form=fields[1],
                upos=fields[3],
                head=head,
                deprel=fields[7],
                line_number=line_number,
            )
        )

    return sentences


def _punctuation_glue_targets(
    source: ConlluSentence, base_labels: dict[int, str]
) -> dict[int, int]:
    """Choose punctuation targets in the original tree before deleting nodes."""
    fixed_ids = {
        token.id for token in source.tokens
        if base_labels[token.id] != "punct" or token.head == 0
    }
    targets: dict[int, int] = {}
    quote_is_open = True
    for token in source.tokens:
        if token.id in fixed_ids:
            continue
        if token.form == '"':
            forward = quote_is_open
            quote_is_open = not quote_is_open
        else:
            forward = all(
                unicodedata.category(character) in {"Ps", "Pi"}
                for character in token.form
            )

        step = 1 if forward else -1
        target_id = token.id + step
        while 1 <= target_id <= len(source.tokens):
            if target_id in fixed_ids:
                targets[token.id] = target_id
                break
            target_id += step
    return targets


def _is_projective_tree(tokens: tuple[ConlluToken, ...]) -> bool:
    """Check for crossing arcs, including the artificial ROOT arc."""
    arcs = [(min(token.id, token.head), max(token.id, token.head)) for token in tokens]
    return not any(
        a < c < b < d or c < a < d < b
        for index, (a, b) in enumerate(arcs)
        for c, d in arcs[index + 1:]
    )


def project_sentence(source: ConlluSentence) -> ProjectedSentence:
    """Project a valid basic tree onto syllable tokens without mutating it."""
    if not source.tokens:
        raise ValueError("Cannot project an empty sentence")
    for expected_id, token in enumerate(source.tokens, start=1):
        if token.id != expected_id:
            raise ValueError(
                f"CoNLL-U line {token.line_number}: IDs must be consecutive from 1"
            )
        if not token.form.split():
            raise ValueError(f"CoNLL-U line {token.line_number}: FORM must not be empty")
    _validate_conllu_tree(list(source.tokens))

    base_labels = {token.id: map_deprel(token.deprel) for token in source.tokens}
    glue_targets = _punctuation_glue_targets(source, base_labels)
    retained = [token for token in source.tokens if token.id not in glue_targets]
    fragments: dict[int, list[str]] = {token.id: [] for token in retained}
    for token in source.tokens:
        fragments[glue_targets.get(token.id, token.id)].append(token.form)

    syllables_by_word: dict[int, list[str]] = {}
    word_to_syllables: dict[int, tuple[int, ...]] = {
        token.id: () for token in source.tokens
    }
    syllable_to_word: dict[int, int] = {}
    next_id = 1
    for token in retained:
        syllables = "".join(fragments[token.id]).split()
        ids = tuple(range(next_id, next_id + len(syllables)))
        syllables_by_word[token.id] = syllables
        word_to_syllables[token.id] = ids
        syllable_to_word.update((syllable_id, token.id) for syllable_id in ids)
        next_id += len(syllables)

    projected_tokens: list[ConlluToken] = []
    for token in retained:
        head = token.head
        # Follow original dependency heads, not the punctuation's textual target.
        while head in glue_targets:
            head = source.tokens[head - 1].head
        external_head = word_to_syllables[head][0] if head else 0
        ids = word_to_syllables[token.id]
        anchor = ids[0]
        for offset, (syllable_id, form) in enumerate(
            zip(ids, syllables_by_word[token.id], strict=True)
        ):
            projected_tokens.append(
                ConlluToken(
                    id=syllable_id,
                    form=form,
                    upos="X",
                    head=external_head if offset == 0 else anchor,
                    deprel=base_labels[token.id] if offset == 0 else "dep",
                    line_number=token.line_number,
                )
            )

    _validate_conllu_tree(projected_tokens)
    tokens = tuple(projected_tokens)
    return ProjectedSentence(
        metadata=dict(source.metadata),
        tokens=tokens,
        word_to_syllables=word_to_syllables,
        syllable_to_word=syllable_to_word,
        is_projective=_is_projective_tree(tokens),
    )
