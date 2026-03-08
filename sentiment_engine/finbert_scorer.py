"""

Scores financial text using ProsusAI/finbert — a BERT model fine-tuned
on financial phrasebank data.

Output classes : positive | negative | neutral
Score mapping  : positive → +confidence, negative → -confidence, neutral → 0

Design notes
------------
* The model is loaded once at class instantiation (lazy, on first call).
  This avoids re-loading the 400 MB weights on every article.
* Long texts are truncated to 512 tokens (BERT's limit).  For articles
  longer than this we score the title + first 400 tokens of body, which
  captures the most signal-dense content.
* Batch processing is used when scoring multiple articles to exploit GPU
  parallelism (falls back gracefully to CPU).
* The scorer exposes a `confidence_threshold` — articles below this value
  are flagged for Claude escalation by the orchestrating pipeline.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from config.logger import get_logger
from sentiment_engine.schemas import ArticleSentiment, ScoringModel, SentimentLabel

log = get_logger(__name__)

# FinBERT label → sentiment direction multiplier
_LABEL_MULTIPLIER = {
    "positive": +1.0,
    "negative": -1.0,
    "neutral":   0.0,
}

# Default confidence threshold below which Claude escalation is triggered
DEFAULT_CONFIDENCE_THRESHOLD = 0.72


class FinBERTScorer:
    """
    Wraps ProsusAI/finbert for article-level sentiment scoring.

    Parameters
    ----------
    model_name            : HuggingFace model ID (default: ProsusAI/finbert)
    confidence_threshold  : scores below this trigger Claude escalation
    batch_size            : articles per forward pass (tune to your GPU VRAM)
    max_tokens            : BERT hard limit — do not exceed 512
    """

    MODEL_NAME = "ProsusAI/finbert"

    def __init__(
        self,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        batch_size:           int   = 16,
        max_tokens:           int   = 512,
    ):
        self.confidence_threshold = confidence_threshold
        self.batch_size           = batch_size
        self.max_tokens           = max_tokens

        # Lazy-loaded on first use
        self._pipeline = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def score_article(
        self,
        ticker:  str,
        url:     str,
        title:   str,
        text:    str,
        published_at,
    ) -> ArticleSentiment:
        """Score a single article. Returns an ArticleSentiment."""
        results = self.score_batch(
            ticker       = ticker,
            urls         = [url],
            titles       = [title],
            texts        = [text],
            published_ats= [published_at],
        )
        return results[0]

    def score_batch(
        self,
        ticker:        str,
        urls:          List[str],
        titles:        List[str],
        texts:         List[str],
        published_ats: list,
    ) -> List[ArticleSentiment]:
        """
        Score a batch of articles in one forward pass.
        Articles are pre-processed and fed to FinBERT in sub-batches.

        Returns
        -------
        List[ArticleSentiment]
            One entry per article, in the same order as the inputs.
            Articles with confidence < threshold have `needs_escalation=True`
            (checked by the pipeline orchestrator).
        """
        self._ensure_loaded()

        inputs      = [self._prepare_text(t, tx) for t, tx in zip(titles, texts)]
        raw_outputs = self._run_pipeline(inputs)

        results: List[ArticleSentiment] = []
        for url, title, published_at, output in zip(urls, titles, published_ats, raw_outputs):

            # FinBERT returns a list of {label, score} dicts (one per class)
            # when top_k=None.  We build a clean dict first.
            scores_dict = {item["label"].lower(): item["score"] for item in output}

            winning_label = max(scores_dict, key=lambda k: scores_dict[k])
            confidence    = scores_dict[winning_label]

            # Map to [-1, +1]
            multiplier    = _LABEL_MULTIPLIER.get(winning_label, 0.0)
            numeric_score = round(multiplier * confidence, 4)

            sentiment_label = ArticleSentiment.label_from_score(numeric_score)

            results.append(ArticleSentiment(
                ticker         = ticker,
                url            = url,
                title          = title,
                published_at   = published_at,
                score          = numeric_score,
                confidence     = round(confidence, 4),
                label          = sentiment_label,
                model_used     = ScoringModel.FINBERT,
                escalated      = False,
                finbert_scores = scores_dict,
            ))

        return results

    def needs_escalation(self, article: ArticleSentiment) -> bool:
        """Return True if this article should be re-scored by Claude."""
        return article.confidence < self.confidence_threshold

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self):
        """Load the model on first use (lazy init)."""
        if self._pipeline is not None:
            return

        try:
            from transformers import pipeline as hf_pipeline
            import torch

            device = 0 if torch.cuda.is_available() else -1
            log.info(
                "Loading FinBERT model '%s' on %s…",
                self.MODEL_NAME,
                "GPU" if device == 0 else "CPU",
            )

            self._pipeline = hf_pipeline(
                task            = "text-classification",
                model           = self.MODEL_NAME,
                tokenizer       = self.MODEL_NAME,
                top_k           = None,      # return scores for ALL classes
                truncation      = True,
                max_length      = self.max_tokens,
                device          = device,
                batch_size      = self.batch_size,
            )
            log.info("FinBERT loaded successfully.")

        except ImportError as exc:
            raise ImportError(
                "transformers and torch are required for FinBERT scoring. "
                "Run: pip install transformers torch"
            ) from exc

    def _prepare_text(self, title: str, body: str) -> str:
        """
        Combine title and body into a single string.
        Title gets 2× weight by repetition — it's the most signal-dense part.
        Body is truncated to keep total length within BERT's token budget.
        """
        # Rough heuristic: 1 token ≈ 4 characters
        max_body_chars = (self.max_tokens - 30) * 4
        truncated_body = body[:max_body_chars] if body else ""
        return f"{title}. {title}. {truncated_body}".strip()

    def _run_pipeline(self, inputs: List[str]) -> list:
        """Run the HuggingFace pipeline in sub-batches."""
        all_outputs = []
        for i in range(0, len(inputs), self.batch_size):
            batch   = inputs[i : i + self.batch_size]
            outputs = self._pipeline(batch)
            all_outputs.extend(outputs)
        return all_outputs