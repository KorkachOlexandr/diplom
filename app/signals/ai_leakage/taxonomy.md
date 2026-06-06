# AI-Leakage Rule Taxonomy

This document is auto-generated from the rules registered in
`app/signals/ai_leakage/rules/`. Each rule targets one specific failure
mode of careless LLM use. Rules are intentionally high-precision and
low-recall — the tool surfaces evidence, not verdicts.

Per-rule precision and recall are measured on the synthetic and HC3
evaluation sets (see Chapter B of the thesis). Rules without measured
operating points have not yet been evaluated; this is tracked as work
in progress.

**Total rules registered:** 19 across 4 families.

## Family: `llm_boilerplate` (3 rules)

### `boilerplate.example_usage_comment` — Boilerplate: 'Example usage:' comment block

LLMs love to append demonstration call sites under a '# Example usage:' header. Plenty of real students also do this, so this rule is one piece of a wider picture rather than a standalone verdict.

- Operating point: not yet measured.

### `boilerplate.note_blocks_repeated` — Boilerplate: multiple 'Note:' comment blocks

Two or more '# Note:' / '"""Note:' blocks in the same file. LLMs love adding sidenotes after every other function. Required threshold of two suppresses the single-note false positive.

- Operating point: not yet measured.

### `boilerplate.time_complexity_inline` — Boilerplate: inline 'Time complexity: O(...)' comment

Inline complexity annotations are a strong tell of LLM-generated explanations dropped into a comment. Honest students more often discuss complexity in prose or skip it entirely.

- Operating point: not yet measured.

## Family: `llm_comment` (9 rules)

### `comment.as_an_ai` — Comment: 'As an AI language model...'

Self-identification of an LLM caught inside a comment. Essentially never written by humans.

- Operating point: not yet measured.

### `comment.certainly_heres` — Comment: 'Certainly! Here is...'

ChatGPT/Claude preamble landing inside a comment block or docstring, e.g. '# Certainly! Here is your sorting function.'

- Operating point: not yet measured.

### `comment.explanation_block` — Comment: 'This function does X' explanatory preamble

Long explanatory natural-language comment preceding a function, matching the pedagogical-explanation style LLMs default to: 'This function takes X and returns Y. It works by ...'.

- Operating point: not yet measured.

### `comment.heres_the` — Comment: 'Here's the [function|code|solution]...'

Service-language comment pasted from an LLM reply: '# Here's the function you requested', '// Here is the code:'. Near-zero false-positive rate in student code.

- Operating point: not yet measured.

### `comment.i_hope_this_helps` — Comment: 'I hope this helps' sign-off

Service-style sign-off LLMs append to coding replies ('I hope this helps!', 'Hope this helps!', 'Let me know if you have any questions'), pasted into the source unchanged. Prefix-free by design — the phrase is distinctive enough that it indicates LLM origin whether it lands in a # comment or inside a triple-quoted docstring block.

- Operating point: not yet measured.

### `comment.ua_as_language_model` — Ukrainian comment: 'Як мовна модель / штучний інтелект'

Ukrainian translation of the canonical AI self-disclosure, landed inside a comment. Forms: «Як мовна модель», «Як ШІ», «Як штучний інтелект».

- Operating point: not yet measured.

### `comment.ua_os_funktsiya` — Ukrainian comment: 'Ось функція/код/розв'язок...'

Service-language Ukrainian comment from an LLM reply pasted into source: «# Ось функція, яку ви просили», «# Ось код для…», «# Ось розв'язок». Direct counterpart to the English comment.heres_the rule.

- Operating point: not yet measured.

### `comment.ua_spodivaius_dopomozhe` — Ukrainian comment: 'Сподіваюся, це допоможе' sign-off

Service-style Ukrainian sign-off LLMs append to replies, left in a comment: «# Сподіваюся, це допоможе!», «# Якщо є питання — звертайтеся».

- Operating point: not yet measured.

### `comment.ua_zvychaino_in_comment` — Ukrainian comment: 'Звичайно/Звісно! Ось...'

Ukrainian-localized assistant preamble caught in a comment: «# Звичайно! Ось ваша функція…», «# Звісно, ось код…».

- Operating point: not yet measured.

## Family: `markdown_leak` (3 rules)

### `markdown.bold_in_code` — Markdown **bold** prose in source (2+ occurrences)

Multiple **bold** spans on prose-style lines inside a source file. Suppresses Python `x ** 2` operator chains by ignoring occurrences whose line starts with an operator character. Designed to surface pasted LLM markdown that survives the copy.

- Operating point: not yet measured.

### `markdown.code_fence_in_source` — Markdown ``` fence left in a source file

Triple-backtick lines in a .py / .cpp / .java file. No legitimate program contains these; they're the unambiguous footprint of a student copying the LLM chat UI verbatim.

- Operating point: not yet measured.

### `markdown.language_fence_in_source` — Markdown ```python fence in source

Language-tagged fences specifically (```python, ```java, ```cpp). High-confidence superset of the bare-fence rule for thesis evidence tables.

- Operating point: not yet measured.

## Family: `policy` (4 rules)

### `policy.cannot_provide_in_comment` — Comment: 'I cannot provide [implementation|code|...]'

LLM refusal to produce code, left as a comment header on a stub function. Useful for catching half-completed submissions with the explanation copied verbatim.

- Operating point: not yet measured.

### `policy.im_sorry_but_in_comment` — Comment: 'I'm sorry, but I cannot...'

Refusal lede pasted into a comment or docstring. Very high precision.

- Operating point: not yet measured.

### `policy.knowledge_cutoff_in_comment` — Comment: knowledge-cutoff disclosure

'My knowledge cutoff is …' or 'as of my last update …' in a comment. LLM-specific disclaimer with effectively zero false-positive rate.

- Operating point: not yet measured.

### `policy.ua_na_zhal` — Ukrainian comment: 'На жаль, я не можу...'

Ukrainian refusal opener pasted into a comment: «# На жаль, я не можу надати повний код…».

- Operating point: not yet measured.

