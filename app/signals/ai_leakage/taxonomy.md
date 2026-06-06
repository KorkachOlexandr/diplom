# AI-Leakage Rule Taxonomy

This document is auto-generated from the rules registered in
`app/signals/ai_leakage/rules/`. Each rule targets one specific failure
mode of careless LLM use. Rules are intentionally high-precision and
low-recall — the tool surfaces evidence, not verdicts.

Per-rule precision and recall are measured on the synthetic and HC3
evaluation sets (see Chapter B of the thesis). Rules without measured
operating points have not yet been evaluated; this is tracked as work
in progress.

**Total rules registered:** 17 across 6 families.

## Family: `markdown_leak` (3 rules)

### `markdown.bold_in_prose` — Markdown bold in plain prose (3+ occurrences)

Multiple **bold** spans in a context that isn't being rendered as Markdown. Common when students paste LLM output into a plain Doc without stripping the asterisks. Threshold of three suppresses false positives from students who legitimately know Markdown.

- Operating point: not yet measured.

### `markdown.code_fences_in_prose` — Triple-backtick fences in a non-code submission

Two or more ``` fences appearing in an otherwise prose submission. Very rare outside of pasted LLM responses.

- Operating point: not yet measured.

### `markdown.headings_in_prose` — Markdown headings in plain prose (2+ occurrences)

Multiple lines starting with `#`/`##`/`###` in a submission that isn't being rendered as Markdown. Strong LLM-output signature.

- Operating point: not yet measured.

## Family: `policy` (3 rules)

### `policy.cannot_browse` — Capability disclosure: 'I can't browse the internet'

LLM-specific tool-availability disclaimer. Pasted verbatim from chat replies.

- Operating point: not yet measured.

### `policy.im_sorry_but` — Refusal opener: 'I'm sorry, but I cannot/can't...'

Stock LLM refusal lede. Very high precision — humans almost never apologize this way in essay-style writing.

- Operating point: not yet measured.

### `policy.no_realtime` — Capability disclosure: 'no access to real-time information'

Standard LLM capability disclaimer. Distinctive enough that no human writer produces this phrasing in a school essay.

- Operating point: not yet measured.

## Family: `preamble` (3 rules)

### `preamble.certainly_heres` — Assistant preamble: 'Certainly! Here is/are...'

Opening assistant-style preamble characteristic of ChatGPT / Claude responses. Students copying without editing leave this in.

- Operating point: not yet measured.

### `preamble.happy_to_help` — Assistant preamble: 'I'd be happy to...'

Service-language opener typical of LLM responses.

- Operating point: not yet measured.

### `preamble.heres_a` — Assistant preamble: 'Here's a/an ...essay/summary/...'

Opening 'Here's a/an [essay|summary|response|analysis|...]' framing — common when an LLM is asked to write a piece and the student pastes the reply.

- Operating point: not yet measured.

## Family: `refusal` (3 rules)

### `refusal.as_an_ai` — Self-identification: 'As an AI language model...'

The textbook LLM self-disclosure. Essentially never written by humans.

- Operating point: not yet measured.

### `refusal.i_cannot` — Refusal artifact: 'I cannot/can't [provide|generate]...'

LLM refusal phrasing left in the pasted output. Students copying a partial refusal often leave the opener intact.

- Operating point: not yet measured.

### `refusal.knowledge_cutoff` — Knowledge-cutoff disclosure

Phrases like 'my knowledge cutoff is...' or 'as of my last update' are LLM-specific disclaimers.

- Operating point: not yet measured.

## Family: `self_id` (3 rules)

### `self_id.developed_by` — Self-identification: 'developed/created by [vendor]'

Vendor attribution that an LLM emits when describing itself. Filters to the specific vendors that ship public LLMs.

- Operating point: not yet measured.

### `self_id.named_model` — Self-identification: 'I am [ChatGPT|Claude|Gemini|...]'

First-person reference to a specific LLM product name. Catches submissions where the student left in a model's self-introduction.

- Operating point: not yet measured.

### `self_id.trained_by` — Self-identification: 'trained by [OpenAI|Anthropic|...]'

Provenance disclosure typical of LLM responses to 'who made you'. Extremely rare in human writing.

- Operating point: not yet measured.

## Family: `template` (2 rules)

### `template.bracket_placeholder` — Unfilled bracket placeholder: '[Your Name]', '[Insert Date]', ...

Square-bracket placeholders that students forget to fill in. High precision; the bracket form is uncommon in normal prose.

- Operating point: not yet measured.

### `template.instruction_echo` — Instruction echo: prompt-like phrasing left in the submission

Phrases like 'Please enter your name', 'Write an essay about', or 'The following is an essay about ...' indicate the student pasted the prompt back instead of removing it.

- Operating point: not yet measured.

