"""
Analyzer domain models.
Re-exports analysis models from app.database.models to maintain single source of truth.
"""
from app.database.models import GroupAnalysis

__all__ = ["GroupAnalysis"]
