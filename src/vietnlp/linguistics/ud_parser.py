"""Input processing, arc-standard transitions and a static training oracle."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from vietnlp.interfaces._common import UD_DEPREL


PROJECTION_VERSION = "v2-first-dep-directional-glue"
TRANSITION_VERSION = "arc-standard-v1"


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


@dataclass(frozen=True)
class Action:
    kind: str
    label: str | None = None


class ParserState:
    """Arc-standard state with final-only attachment to ROOT."""

    def __init__(self, tokens: tuple[str, ...]) -> None:
        self.tokens = tuple(tokens)
        if not self.tokens:
            raise ValueError("Cannot initialize a parser state with empty input")
        if any(
            not isinstance(form, str) or not form or any(char.isspace() for char in form)
            for form in self.tokens
        ):
            raise ValueError("Parser tokens must be nonempty syllables without whitespace")
        self.stack: list[int] = [0]
        self.buffer_pos = 1
        self.heads: list[int | None] = [None] * (len(self.tokens) + 1)
        self.labels: list[str | None] = [None] * (len(self.tokens) + 1)

    @property
    def is_terminal(self) -> bool:
        return self.buffer_pos == len(self.tokens) + 1 and self.stack == [0]

    def _can_attach(self, head: int, dependent: int, label: str | None) -> bool:
        n = len(self.tokens)
        if type(head) is not int or type(dependent) is not int:
            return False
        if not 0 <= head <= n or not 1 <= dependent <= n or head == dependent:
            return False
        if len(self.heads) != n + 1 or len(self.labels) != n + 1:
            return False
        if self.heads[dependent] is not None or self.labels[dependent] is not None:
            return False
        if not isinstance(label, str) or label not in UD_DEPREL:
            return False
        if (head == 0) != (label == "root"):
            return False
        if head == 0 and any(parent == 0 for parent in self.heads[1:]):
            return False

        seen: set[int] = set()
        current = head
        while current != 0:
            if type(current) is not int or not 1 <= current <= n:
                return False
            if current == dependent or current in seen:
                return False
            seen.add(current)
            parent = self.heads[current]
            if parent is None:
                return True
            current = parent
        return True

    def _is_legal(self, action: Action) -> bool:
        if not isinstance(action, Action):
            return False
        if action.kind == "SHIFT":
            return (
                action.label is None
                and type(self.buffer_pos) is int
                and 1 <= self.buffer_pos <= len(self.tokens)
            )
        if action.kind not in {"LEFT_ARC", "RIGHT_ARC"} or len(self.stack) < 2:
            return False

        left, right = self.stack[-2:]
        head, dependent = (right, left) if action.kind == "LEFT_ARC" else (left, right)
        if not self._can_attach(head, dependent, action.label):
            return False
        if head == 0:
            return (
                action.kind == "RIGHT_ARC"
                and self.buffer_pos == len(self.tokens) + 1
                and self.stack == [0, dependent]
            )
        return True

    def legal_actions(self) -> tuple[Action, ...]:
        """List legal actions in SHIFT, LEFT_ARC, RIGHT_ARC order."""
        candidates = [Action("SHIFT")]
        for kind in ("LEFT_ARC", "RIGHT_ARC"):
            for label in sorted(UD_DEPREL):
                if kind != "LEFT_ARC" or label != "root":
                    candidates.append(Action(kind, label))
        return tuple(action for action in candidates if self._is_legal(action))

    def apply(self, action: Action) -> None:
        """Validate an action before updating any state field."""
        if not self._is_legal(action):
            raise ValueError(f"Illegal parser action: {action!r}")
        if action.kind == "SHIFT":
            self.stack.append(self.buffer_pos)
            self.buffer_pos += 1
            return

        left, right = self.stack[-2:]
        head, dependent = (right, left) if action.kind == "LEFT_ARC" else (left, right)
        self.heads[dependent] = head
        self.labels[dependent] = action.label
        if action.kind == "LEFT_ARC":
            del self.stack[-2]
        else:
            self.stack.pop()


class StaticOracle:
    """Choose gold arc-standard actions for a projected projective tree."""

    def __init__(self, gold: ProjectedSentence) -> None:
        self.sent_id = gold.metadata.get("sent_id", "<unknown>")
        self.tokens = tuple(token.form for token in gold.tokens)
        try:
            if not gold.tokens:
                raise ValueError("empty gold sentence")
            for expected_id, token in enumerate(gold.tokens, start=1):
                if token.id != expected_id:
                    raise ValueError("gold IDs must be consecutive from 1")
                if not token.form or any(char.isspace() for char in token.form):
                    raise ValueError("gold tokens must be nonempty syllables")
                if token.deprel not in UD_DEPREL:
                    raise ValueError(f"invalid gold label: {token.deprel!r}")
            _validate_conllu_tree(list(gold.tokens))
            if not _is_projective_tree(gold.tokens):
                raise ValueError("non-projective gold tree")
        except ValueError as exc:
            raise ValueError(f"Static oracle {self.sent_id}: {exc}") from exc

        self.gold_heads = (None,) + tuple(token.head for token in gold.tokens)
        self.gold_labels = (None,) + tuple(token.deprel for token in gold.tokens)
        children: list[list[int]] = [[] for _ in range(len(gold.tokens) + 1)]
        for token in gold.tokens:
            children[token.head].append(token.id)
        self.gold_children = tuple(tuple(group) for group in children)

    def _check_state(self, state: ParserState) -> None:
        """Check token alignment and state indices before accessing gold arrays."""
        n = len(self.tokens)
        if (
            state.tokens != self.tokens
            or len(state.heads) != n + 1
            or len(state.labels) != n + 1
            or type(state.buffer_pos) is not int
            or not 1 <= state.buffer_pos <= n + 1
            or not state.stack
            or state.stack[0] != 0
            or any(type(index) is not int or not 0 <= index <= n for index in state.stack)
        ):
            raise ValueError(f"Static oracle {self.sent_id}: state does not match gold")

    def is_ready(self, state: ParserState, dependent_id: int) -> bool:
        """Require every direct gold child to have its gold head and label."""
        self._check_state(state)
        if type(dependent_id) is not int or not 1 <= dependent_id <= len(self.tokens):
            raise ValueError(f"Static oracle {self.sent_id}: invalid dependent ID")
        return all(
            state.heads[child] == dependent_id
            and state.labels[child] == self.gold_labels[child]
            for child in self.gold_children[dependent_id]
        )

    def next_action(self, state: ParserState) -> Action:
        """Select LEFT_ARC, RIGHT_ARC or SHIFT without changing the state."""
        self._check_state(state)
        if state.is_terminal:
            raise ValueError(f"Static oracle {self.sent_id}: terminal state has no action")

        if len(state.stack) >= 2:
            left, right = state.stack[-2:]
            for kind, head, dependent in (
                ("LEFT_ARC", right, left), ("RIGHT_ARC", left, right),
            ):
                if dependent == 0 or self.gold_heads[dependent] != head:
                    continue
                action = Action(kind, self.gold_labels[dependent])
                if self.is_ready(state, dependent) and state._is_legal(action):
                    return action

        shift = Action("SHIFT")
        if state._is_legal(shift):
            return shift
        raise ValueError(
            f"Static oracle {self.sent_id}: no gold action; "
            f"stack={state.stack}, buffer_pos={state.buffer_pos}, "
            f"heads={state.heads}, labels={state.labels}"
        )


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
