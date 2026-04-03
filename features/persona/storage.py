"""JSON file persistence for personas. One file per persona_id."""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import Optional

from .models import PurchasePersona

PERSONAS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "personas")


def _path(persona_id: str) -> str:
    os.makedirs(PERSONAS_DIR, exist_ok=True)
    return os.path.join(PERSONAS_DIR, f"{persona_id}.json")


def load(persona_id: str) -> Optional[PurchasePersona]:
    path = _path(persona_id)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    return PurchasePersona(**data)


def save(persona: PurchasePersona) -> None:
    persona.updated_at = datetime.now(timezone.utc)
    path = _path(persona.persona_id)
    with open(path, "w") as f:
        json.dump(persona.model_dump(), f, indent=2, default=str)


def load_or_create(persona_id: str, display_name: str = "My Profile") -> PurchasePersona:
    existing = load(persona_id)
    if existing:
        return existing
    persona = PurchasePersona(persona_id=persona_id, display_name=display_name)
    save(persona)
    return persona


def list_personas() -> list[str]:
    os.makedirs(PERSONAS_DIR, exist_ok=True)
    return [f[:-5] for f in os.listdir(PERSONAS_DIR) if f.endswith(".json")]
