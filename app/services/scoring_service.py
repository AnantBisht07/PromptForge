STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "or", "and", "but", "if",
    "then", "that", "this", "it", "its", "not", "so", "yet", "both",
    "nor", "just", "me", "my", "we", "you", "he", "she", "they",
}


def score_output(prompt: str, output: str) -> float:
    """
    Score the quality of an LLM output relative to the original prompt.

    Scoring strategy (two signals, weighted):
      1. Keyword coverage  (70 %) — how many meaningful words from the
         prompt also appear in the output? Higher coverage = more relevant.
      2. Length bonus      (30 %) — longer responses tend to be more
         complete; bonus caps at 50 words so verbosity isn't gamed.

    Final score is mapped onto the [1.0, 10.0] range and rounded to 2 dp.

    In production you would replace this with an LLM-as-judge call or a
    dedicated reward model — this simple heuristic is intentionally
    transparent so students can trace exactly how the number is derived.
    """
    # --- extract keywords from the prompt ---
    def clean(word: str) -> str:
        return word.lower().strip(".,!?;:\"'()[]{}")

    prompt_keywords = {
        clean(w)
        for w in prompt.split()
        if len(clean(w)) > 2 and clean(w) not in STOP_WORDS
    }

    # If the prompt has no meaningful words, return a neutral score
    if not prompt_keywords:
        return 5.0

    output_lower = output.lower()

    # Signal 1: fraction of prompt keywords found anywhere in the output
    matched = sum(1 for kw in prompt_keywords if kw in output_lower)
    keyword_coverage = matched / len(prompt_keywords)

    # Signal 2: normalised response length (caps at 50 words → bonus = 1.0)
    word_count = len(output.split())
    length_bonus = min(word_count / 50.0, 1.0)

    # Weighted combination → mapped from [0, 1] to [1, 10]
    raw = keyword_coverage * 0.7 + length_bonus * 0.3
    score = 1.0 + raw * 9.0

    return round(score, 2)
