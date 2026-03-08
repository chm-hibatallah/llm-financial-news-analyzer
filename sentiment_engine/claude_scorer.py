"""

Re-scores articles that FinBERT was not confident about using Claude.

When to escalate
----------------
FinBERT is trained on financial phrasebank sentences and performs well on
clean, short statements.  It struggles with:
  - Sarcasm / irony  ("Great, another earnings miss…")
  - Mixed signals    ("Strong revenue but margins collapsed")
  - Ambiguous framing("Tesla cuts prices AGAIN")

Claude handles these cases naturally.  To keep API costs manageable:
  - Only articles below the confidence threshold are escalated.
  - We send title + description only (not full article body) to stay within
    a small token budget per call.
  - Results are cached by (url hash) so the same article is never re-scored.

"""

from __future__ import annotations

import hashlib
import json
import os
from typing import List, Optional

import anthropic

from config.logger import get_logger
from config.settings import CACHE_DIR
from sentiment_engine.schemas import ArticleSentiment, ScoringModel, SentimentLabel

log = get_logger(__name__)

# Claude model to use for escalation (cheap + fast is fine here)
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# Approximate max input tokens per article (title + description is usually < 200)
MAX_TOKENS_PER_CALL = 256

SYSTEM_PROMPT = """You are a financial sentiment analyst.
You will be given a news article headline and description about a publicly traded company.

Respond ONLY with a valid JSON object — no preamble, no explanation, no markdown fences.

The JSON must have exactly these keys:
{
  "score": <float between -1.0 and 1.0>,
  "label": <one of: "bearish", "neutral", "bullish">,
  "confidence": <float between 0.0 and 1.0>,
  "reason": <one sentence explaining your score>
}

Scoring guide:
  +1.0  = extremely bullish (blowout earnings, major positive catalyst)
  +0.5  = moderately bullish (beat estimates, positive product news)
   0.0  = neutral (routine update, no clear directional signal)
  -0.5  = moderately bearish (missed estimates, regulatory concern)
  -1.0  = extremely bearish (fraud, bankruptcy, catastrophic news)

Be precise. Most articles fall in the [-0.5, +0.5] range."""


class ClaudeScorer:
    """
    Escalation scorer that uses Claude to re-score low-confidence articles.

    Parameters
    ----------
    api_key    : Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
    use_cache  : whether to cache results by article URL hash (recommended)
    """

    def __init__(
        self,
        api_key:   Optional[str] = None,
        use_cache: bool          = True,
    ):
        self._client   = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.use_cache = use_cache
        self._cache:   dict[str, dict] = {}       # in-memory cache
        self._cache_path = os.path.join(CACHE_DIR, "claude_scores.json")
        self._load_disk_cache()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def rescore(self, article: ArticleSentiment, body_text: str = "") -> ArticleSentiment:
        """
        Re-score a single article using Claude.
        Returns a NEW ArticleSentiment with updated fields and escalated=True.

        Parameters
        ----------
        article   : the original FinBERT-scored ArticleSentiment
        body_text : optional article body (we only send title + description
                    to keep tokens low — body_text is ignored by default)
        """
        cache_key = self._url_hash(article.url)

        # Check cache first
        if self.use_cache and cache_key in self._cache:
            log.debug("Claude cache hit for %s", article.url[:60])
            return self._apply_cached(article, self._cache[cache_key])

        log.info("Escalating to Claude: '%s…'", article.title[:60])

        try:
            result = self._call_claude(article.title, article.title)
        except Exception as exc:
            log.warning("Claude escalation failed for '%s': %s — keeping FinBERT score.", article.title[:60], exc)
            return article     # fall back to FinBERT result on failure

        # Cache and persist
        if self.use_cache:
            self._cache[cache_key] = result
            self._save_disk_cache()

        return self._build_rescored_article(article, result)

    def rescore_batch(
        self,
        articles:   List[ArticleSentiment],
        body_texts: Optional[List[str]] = None,
    ) -> List[ArticleSentiment]:
        """
        Re-score a list of articles.  Each article gets its own API call
        (Claude doesn't support true batching for text-classification prompts).
        """
        body_texts = body_texts or [""] * len(articles)
        results    = []

        for article, body in zip(articles, body_texts):
            rescored = self.rescore(article, body)
            results.append(rescored)

        log.info("Claude escalation complete: %d articles re-scored.", len(results))
        return results

    # ------------------------------------------------------------------
    # Claude API call
    # ------------------------------------------------------------------

    def _call_claude(self, title: str, description: str) -> dict:
        """
        Send one article to Claude and return the parsed JSON response.
        Raises ValueError if the response cannot be parsed.
        """
        user_message = f"Headline: {title}\nDescription: {description or 'N/A'}"

        response = self._client.messages.create(
            model      = CLAUDE_MODEL,
            max_tokens = MAX_TOKENS_PER_CALL,
            system     = SYSTEM_PROMPT,
            messages   = [{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text.strip()

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            # Sometimes Claude wraps JSON in ```json … ``` despite instructions
            cleaned = raw_text.replace("```json", "").replace("```", "").strip()
            parsed  = json.loads(cleaned)

        # Validate required keys
        required = {"score", "label", "confidence", "reason"}
        if not required.issubset(parsed.keys()):
            raise ValueError(f"Claude response missing keys: {required - set(parsed.keys())}")

        # Clamp values to valid ranges
        parsed["score"]      = max(-1.0, min(1.0, float(parsed["score"])))
        parsed["confidence"] = max(0.0,  min(1.0, float(parsed["confidence"])))

        return parsed

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_rescored_article(
        self, original: ArticleSentiment, claude_result: dict
    ) -> ArticleSentiment:
        """Merge Claude's result into a new ArticleSentiment."""
        score = claude_result["score"]
        return ArticleSentiment(
            ticker         = original.ticker,
            url            = original.url,
            title          = original.title,
            published_at   = original.published_at,
            score          = round(score, 4),
            confidence     = round(claude_result["confidence"], 4),
            label          = ArticleSentiment.label_from_score(score),
            model_used     = ScoringModel.CLAUDE,
            escalated      = True,
            finbert_scores = original.finbert_scores,
            claude_reason  = claude_result.get("reason"),
        )

    def _apply_cached(self, original: ArticleSentiment, cached: dict) -> ArticleSentiment:
        return self._build_rescored_article(original, cached)

    @staticmethod
    def _url_hash(url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def _load_disk_cache(self):
        if not self.use_cache or not os.path.exists(self._cache_path):
            return
        try:
            with open(self._cache_path, "r") as f:
                self._cache = json.load(f)
            log.debug("Loaded %d cached Claude scores from disk.", len(self._cache))
        except Exception as exc:
            log.warning("Could not load Claude score cache: %s", exc)

    def _save_disk_cache(self):
        try:
            with open(self._cache_path, "w") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as exc:
            log.warning("Could not save Claude score cache: %s", exc)