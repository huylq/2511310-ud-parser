# Week 3 Tasks — Project 2: UD Dependency Parsing

**Professor's evaluation of your Week 2 submission (commits `a28c82a`,
`8fd3528` and `f717d44`, `WEEK2_REPORT.md`) is below, followed by this
week's tasks. A Vietnamese summary is at the end of this file.**

## Week 2 evaluation: PASS on the work; two required report items are missing

### What I checked

- **The suite:** I ran it on `f717d44`. The full suite is green, and
  `tests/test_linguistics_ud_parser_hand_annotated.py` passes all 24 of
  its cases (20 sentences plus 4 file-level checks), matching your report.
- **Your VTB counts reproduce.** I recounted VTB at the commit you name,
  independently of your script:
  - split sizes 1,400 / 1,123 / 800 sentences;
  - 20,215 / 26,162 / 11,692 word tokens;
  - 4,535 / 5,497 / 2,079 multisyllabic tokens;
  - 5 / 9 / 1 non-projective trees (with the ROOT arc included);
  - 84 source labels, which map to 34 base labels.

  Your construction counts also match where we used the same criteria
  (đó as `det:pmod` 171; đấy as `discourse` 10 of 17; nhé 5 of 5).
- **The annotation set:**
  - 20 sentences, all with full source URLs (VnExpress, Tuổi Trẻ,
    Thanh Niên, CafeF, and the VOZ, Tinh tế, OTOFUN and Kênh Sinh Viên
    forums);
  - 0 synthetic, and 5 marked `uncertain`;
  - registers: 10 formal, 5 informal, 5 teencode;
  - 10 construction tags covered, which meets the target.
- **Scope:**
  - the VTB files are not committed;
  - there is no `ud_parser.py` and no training code yet, as required;
  - your diff touches only your owned paths.
- **English:** `DESIGN.md`, `TESTING.md` and the report are fully in
  English, and the rule-based decision is marked as superseded.

### What was done well

- **The design is implementable as written.** §5 (state, legal actions,
  the guard, final-only ROOT) and §6 (the static oracle with its "ready"
  condition on labels as well as heads) are precise enough to write tests
  from directly. That is exactly what Weeks 1-2 were for.
- **The single-root argument is structural.** ROOT can only be assigned
  by the final `RIGHT_ARC` from stack `[0, j]` with the buffer exhausted,
  so one root follows from the transition system. Nothing has to patch it
  up afterwards.
- **Group mapping by minimum depth.** Your argument in §11.2 is right:
  under minimum depth, a non-root group's representative can't have its
  parent inside the same group, so the grouped tree is acyclic. It's
  rare to see a student prove that rather than hope for it.
- **No gold UPOS features, no pickle, a fixed weight budget, and test
  used once.** Every constraint from the Week 2 decision is designed in.
- **Honest limits.** The report says plainly that post-projection counts,
  UAS/LAS and timings are unmeasured. Keep that habit.

### Required fixes (do these first, today)

The self-check in `week2_tasks.md` had two items that are missing from
`WEEK2_REPORT.md`:

1. **The data statement.** Add this sentence, word for word: *"No AI,
   LLM, or generative or trained model was used to find, write,
   translate, annotate or clean any data in this submission."*
2. **The AI-use disclosure table** at the very end of the report: one
   row per tool, with the tool, its version, the prompts, what the AI
   produced, and what you changed. It covers all AI use in Week 2,
   including documents, the report, `analyze_vtb.py` and the contract
   test. If you used none, write "AI used: none".

Use of AI on prose or code is allowed if it is disclosed. Leaving the
table out is not. Add both items in one commit before any Week 3 work.

### Design points to settle this week

- **Opening punctuation (§4.1, step 2).** VTB has no `SpaceAfter`, so
  every punctuation token is space-separated. Your rule glues each one to
  the *preceding* token. That matches stub input for `.`, `,` and `:`, but
  not for opening brackets and quotes, which attach to the *following*
  word in written text:
  - the source text `lại : " Coi` projects to `lại:"` and `Coi`;
  - the stub, run on the real sentence `lại: "Coi`, gives `lại:` and
    `"Coi`.

  My count shows that VTB train has 408 `"` and 27 `(` tokens labelled
  `punct`. Reproduce this with your own script before you cite it. Either
  glue opening punctuation forward (for straight quotes, alternate
  open/close within the sentence), or keep your rule and show on dev that
  it doesn't matter. Your planned glued-versus-separate comparison should
  include this case. Record your decision in `DESIGN.md` and bump
  `projection_version` if the rule changes.
- **Where the code lives.** Your owned paths are `ud_parser.py`,
  `ud_model/**`, `tests/test_linguistics_ud_parser*.py` and this folder.
  Tests in `tests/` must be able to import what they test, so:
  - the reader, label mapping, projection, transition system and oracle
    go in `src/vietnlp/linguistics/ud_parser.py`;
  - the training command line goes in
    `student-projects/02-ud-parsing/scripts/`, and imports from
    `ud_parser`.

  Don't create new modules outside your owned paths.

### Process notes

- **Schedule:** you are still about four weeks behind `plan.md`. Week 2
  closed the design phase properly, so you can now catch up quickly. This
  week covers the first half of the "Weeks 3-4" block in
  `week2_tasks.md`.
- **Tests must not need VTB.** VTB is not committed, so the offline suite
  can't read it. Unit tests use small CoNLL-U strings you write by hand
  inside the test file, plus your committed `data/hand_annotated.conllu`.
  Scripts that read VTB print measurements; they are not tests.

## This week's scope

Build the data side of the parser, **test first**. Each item gets a
failing test that you commit red, then the code that makes it green, as
Project 8 does: the red commit is your evidence.
- the CoNLL-U reader;
- the label mapping;
- the projection;
- the transition system with its guard;
- the static oracle.

Then run the projection over VTB and report the counts it produces.

**Not this week:** features, the perceptron, training and `parse()`. They
are next week, once the oracle is proven.

### Data rule (unchanged)

**Collect and annotate all data by hand. Do not use AI, an LLM, or any
generative or trained model to produce data.**
- VTB is published, human-annotated data. You may read it, count it,
  convert it with deterministic code you wrote, and train on it.
- **This applies to AI assistants too:** no AI-suggested sentences, test
  cases or labels.
- **Your own parser must never pre-annotate data either.**
- The small CoNLL-U snippets in your tests are test data: write them by
  hand, and say in a comment what each one is for.
- **AI help with prose or code must be disclosed** in the table at the end
  of your report.

### 0. Report fixes (above)

Make one commit before anything else.

### 1. CoNLL-U reader

`read_conllu(text: str) -> list[...]`: your own sentence and node types,
kept separate from the frozen interface types. Tests first:
- **A two-sentence snippet:** returns two sentences, with `sent_id`,
  `text`, FORM, HEAD and DEPREL read correctly.
- **Multiword ranges (`3-4`) and empty nodes (`5.1`)** are skipped.
  Basic-tree integer IDs only, as `DESIGN.md` §2 says.
- **Malformed input raises `ValueError` naming the line number:**
  - the wrong column count;
  - a non-integer HEAD;
  - IDs that are not consecutive from 1;
  - a HEAD that points outside the sentence.
- **Your hand-annotated set loads:** `data/hand_annotated.conllu` gives
  20 sentences, and every one passes your reader's tree check.

### 2. Label mapping

- **Subtypes map to base labels:** `clf:det → clf`,
  `compound:svc → compound`, `nmod:poss → nmod`.
- **Every mapped label is in `UD_DEPREL`.** Parametrize over the full table
  in `DESIGN.md` §14. That table is data, so build it once in code and
  test it; don't keep a second copy by hand.
- **An unknown label raises.** Never map it to `dep` silently.

### 3. Projection (`DESIGN.md` §4.1)

Each case is a hand-written snippet with its expected output written out
in the test:
1. **A two-syllable word** (`Hoa Kỳ`) becomes two tokens. The second
   attaches to the first with `dep`, and the word's external arcs go
   through the first.
2. **A three-syllable word:** both later syllables attach directly to the
   anchor, not in a chain.
3. **Trailing punctuation** glues onto the preceding token without a
   space (`Nội` + `.` → `Nội.`). Its arc disappears.
4. **A dependent whose head is a deleted punctuation token** follows the
   original head chain to the first retained ancestor and keeps its own
   relation.
5. **Leading punctuation** with nothing before it is kept.
6. **A punctuation root** is kept.
7. **Opening punctuation:** whatever you decided above, pinned by a test.
8. **The mappings round-trip:** word to syllables, and syllables back to
   the word.
9. **Every projected tree** passes `is_single_rooted_tree` once converted
   to the interface types. Run this over your 20 hand-annotated sentences
   too, read as source trees.

### 4. Transition system and guard (`DESIGN.md` §5)

Test the class directly, without any model:
- **The initial state** is stack `[0]`, `buffer_pos` 1, and every head
  `None`.
- **Illegal actions are rejected, and the state is unchanged afterwards.**
  Compare a deep copy of the state before and after. Cover:
  - `SHIFT` on an empty buffer;
  - `LEFT_ARC` with ROOT as the dependent;
  - an arc onto a token that already has a head;
  - a self-loop;
  - a cycle-closing arc. Name this test with `cycle`, because the gate
    looks for that input class.
- **`RIGHT_ARC(root)`:**
  - is illegal while the buffer has input;
  - is illegal when the stack holds more than `[0, j]`;
  - is legal exactly once, at the end.
- **The legal-action set** in three hand-built states equals the set you
  work out by hand.
- **Termination:** a full successful run uses exactly `2n` actions,
  `n` SHIFTs and `n` arcs.

### 5. Static oracle (`DESIGN.md` §6)

- **Round trip on hand-written trees:** the oracle's action sequence,
  replayed through §4, reproduces every gold head and label exactly.
  Cover:
  - a single token;
  - a left-headed chain;
  - a right-headed chain;
  - a head with three dependents on both sides;
  - one tree with a `clf` arc (the `clf` input class).
- **Round trip on every projective sentence** in your projected
  hand-annotated set.
- **A non-projective snippet** makes the oracle raise an error naming the
  `sent_id`. It must not loop forever, and it must not return a wrong
  sequence. Name this test with `adversarial`.
- **An empty or one-token sentence** behaves as `DESIGN.md` says (the
  `degenerate` input class).

### 6. Measure the projection on VTB (script, not test)

Add `scripts/project_vtb.py`. It reads the VTB files from a path you pass
on the command line, projects every split, and replays the oracle on
train. Commit its output as `analysis/PROJECTION_COUNTS.md` and `.json`.
Report per split:
- syllable tokens after projection;
- the number of `dep` arcs added inside words;
- punctuation glued (trailing vs opening);
- invalid projected trees, and **non-projective projected trees**. This
  is the number `DESIGN.md` §2 says you must not infer from the source
  count;
- train sentences excluded, by ID and reason;
- oracle failures on the remaining train sentences. **This should be 0;**
  any failure is a bug to investigate, not a sentence to drop.

Then update `DESIGN.md` §2 and §4 with the measured numbers.

## Self-check before you call Week 3 done

- [ ] `WEEK2_REPORT.md` has the data statement and a complete AI-use
      disclosure table (one commit, done first).
- [ ] The opening-punctuation decision is recorded in `DESIGN.md` and
      pinned by a test.
- [ ] §1-§5 are in `ud_parser.py`, each test committed red before its
      code. `WEEK3_REPORT.md` lists the red and green commit for each
      group.
- [ ] Your test names include the `cycle`, `clf`, `adversarial` and
      `degenerate` classes, and no test reads VTB.
- [ ] `analysis/PROJECTION_COUNTS.*` is committed. There are 0 oracle
      failures on retained train sentences, or each failure is explained
      and fixed.
- [ ] The full `pytest tests` line is in `WEEK3_REPORT.md` (English).
- [ ] The report contains the data statement and ends with an AI-use
      disclosure table, or "AI used: none".

## What NOT to do this week

- Don't write features, the perceptron or `parse()` yet.
- Don't commit VTB, any part of it, or test snippets copied from it. Write
  your own snippets.
- Don't use pickle, and don't add dependencies.
- Don't use any model or AI assistant to produce test trees or labels.
- Don't touch `src/vietnlp/interfaces/**` or `tests/fixtures/**`.

## Commit & push

Push to `student/02-ud-parsing` as you go, with small commits and the
red commit before the green one. Before you push, `git log --oneline`
should read as test → code → test → code.

## Looking ahead

- **Week 4:** the 54 features (with a determinism test), the averaged
  perceptron, and training on a small train subset. `parse()` loads
  committed weights from `ud_model/` and returns a valid tree for all 151
  fixture sentences, with the `:))` override. The gate's schema and tree
  checks should pass from then on.
- **Weeks 5-6:** full training, tuning on dev, pruning to the budget,
  `ATTRIBUTION.md`.

---

## Tóm tắt bằng tiếng Việt

**Đánh giá Tuần 2: ĐẠT về nội dung, nhưng báo cáo còn thiếu hai mục bắt buộc.**

- **Đã kiểm chứng:**
  - Toàn bộ test suite pass; contract test cho 20 câu tự gán nhãn pass
    đủ 24 trường hợp.
  - Mọi số liệu VTB em nêu (số câu, số token, số cây không xạ ảnh 5/9/1,
    84 nhãn → 34 nhãn gốc) đều tái lập đúng.
  - Thiết kế (arc-standard, oracle, ánh xạ nhóm theo độ sâu nhỏ nhất)
    rất chặt chẽ, đủ để viết test trực tiếp.
- **Phải sửa ngay (một commit, trước mọi việc khác):** thêm vào
  `WEEK2_REPORT.md`:
  - câu cam kết về dữ liệu, đúng nguyên văn;
  - bảng khai báo sử dụng AI ở cuối báo cáo, hoặc "AI used: none".
- **Điểm thiết kế cần chốt:** quy tắc dán dấu câu vào token *trước* đúng
  với `.`, `,` và `:`, nhưng sai với ngoặc mở và dấu nháy mở. Trong văn
  bản thật, chúng dính vào từ *sau*. Hãy quyết định, ghi vào `DESIGN.md`
  và viết test.
- **Tuần này:** viết test trước rồi mới viết code (commit đỏ trước, xanh
  sau) cho:
  - bộ đọc CoNLL-U;
  - ánh xạ nhãn;
  - phép chiếu VTB;
  - hệ chuyển trạng thái và guard;
  - oracle tĩnh.

  Sau đó chạy phép chiếu trên toàn bộ VTB và báo cáo số cây không hợp lệ
  hoặc không xạ ảnh *sau khi chiếu*. Số lỗi oracle trên train phải bằng 0.
- **Chưa làm:** features, perceptron và `parse()` để sang Tuần 4.
  Test không được đọc VTB.
