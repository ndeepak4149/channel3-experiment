"""
Feature 6: Purchase Persona Memory
====================================
Lightweight preference profile that persists across sessions.
Learns from basket additions (brand, price tier, category, deal behaviour)
and supports explicit declarations.

Usage:
    from features.persona import get_persona, observe_pick, declare

    persona = get_persona("user_deepak")
    persona = observe_pick(persona, product, was_on_sale=False)
    persona = declare(persona, "brand_prefer", "Nike")
    persona = declare(persona, "size", "shoes_us", "10")
"""
from .storage import load_or_create, save, load, list_personas
from .inference import observe_product_pick, apply_declaration
from .bias import personalized_weights, persona_score_adjustment
from .models import PurchasePersona


def get_persona(persona_id: str, display_name: str = "My Profile") -> PurchasePersona:
    return load_or_create(persona_id, display_name)


def observe_pick(
    persona: PurchasePersona,
    product,
    was_on_sale: bool = False,
    auto_save: bool = True,
) -> PurchasePersona:
    updated = observe_product_pick(persona, product, was_on_sale)
    if auto_save:
        save(updated)
    return updated


def declare(
    persona: PurchasePersona,
    declaration_type: str,
    value: str,
    extra: str = "",
    auto_save: bool = True,
) -> tuple[PurchasePersona, str]:
    updated, msg = apply_declaration(persona, declaration_type, value, extra)
    if auto_save:
        save(updated)
    return updated, msg


__all__ = [
    "get_persona", "observe_pick", "declare",
    "get_persona", "save", "load", "list_personas",
    "personalized_weights", "persona_score_adjustment",
    "PurchasePersona",
]
