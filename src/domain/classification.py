from dataclasses import dataclass


@dataclass(frozen=True)
class Classification:
    category: str
    confidence: float

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0.")

        if not self.category:
            raise ValueError("Category cannot be empty.")