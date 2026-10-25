"""CoNLL-U input for the Vietnamese dependency parser."""

from __future__ import annotations

from dataclasses import dataclass
import re


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
