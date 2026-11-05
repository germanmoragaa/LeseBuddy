from dataclasses import dataclass, field

from app.services.translation.provider import UsageSnapshot


@dataclass
class FakeTranslationProvider:
    """In-memory test double — the only TranslationProvider CI ever uses. Deterministic:
    returns `f"[{target_lang}] {text}"` so tests can assert on the exact output. Set
    `fail_with` to an exception instance before a call to simulate a provider failure."""

    calls: list[tuple[str, str | None, str]] = field(default_factory=list)
    usage: UsageSnapshot = field(
        default_factory=lambda: UsageSnapshot(characters_used=0, character_limit=500_000)
    )
    fail_with: Exception | None = None

    def translate(self, text: str, *, context: str | None, target_lang: str) -> str:
        if self.fail_with is not None:
            raise self.fail_with
        self.calls.append((text, context, target_lang))
        return f"[{target_lang}] {text}"

    def get_usage(self) -> UsageSnapshot:
        return self.usage
