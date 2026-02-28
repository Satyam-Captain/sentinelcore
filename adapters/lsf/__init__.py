# File: adapters/lsf/__init__.py
"""LSF scheduler adapter package.

This package contains scheduler-translation code only.
No diagnosis, no DM semantics.
"""
from __future__ import annotations
from .scheduler_adapter import LsfSchedulerAdapter

__all__ = ["LsfSchedulerAdapter"]

