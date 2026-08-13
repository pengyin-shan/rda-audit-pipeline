import os
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Config:
    data_dir: Path = field(default_factory=lambda: Path.cwd() / "data")
    corpus_path: Path = field(default_factory=lambda: Path.cwd() / "corpus.csv")
    github_token: str | None = None
    contact: str = "set-AUDIT_CONTACT-env-var"

    def __post_init__(self):
        self.data_dir = Path(self.data_dir)
        self.corpus_path = Path(self.corpus_path)

    @classmethod
    def from_env(cls, corpus_path=None, data_dir=None):
        return cls(
            data_dir=Path(data_dir) if data_dir else Path.cwd() / "data",
            corpus_path=Path(corpus_path) if corpus_path else Path.cwd() / "corpus.csv",
            github_token=os.environ.get("GITHUB_TOKEN"),
            contact=os.environ.get("AUDIT_CONTACT", "set-AUDIT_CONTACT-env-var"),
        )

    @property
    def raw(self) -> Path:
        return self.data_dir / "raw"          # immutable API snapshots

    @property
    def norm(self) -> Path:
        return self.data_dir / "normalized"   # per-project canonical records

    @property
    def results(self) -> Path:
        return self.data_dir / "results"      # analysis outputs

    def ua(self) -> dict:
        return {"User-Agent":
                f"rda-audit-pipeline/0.2 (research metadata audit; {self.contact})"}

    def gh_headers(self) -> dict:
        h = self.ua()
        h["Accept"] = "application/vnd.github+json"
        if self.github_token:
            h["Authorization"] = f"Bearer {self.github_token}"
        return h
