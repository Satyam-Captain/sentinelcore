# File: modules/dm_doctor/rules/__init__.py
"""DM-Doctor diagnostic rules.


Rules are pure, deterministic, and consume NormalizedContext only.
"""


from .no_transfer_jobs import NoTransferJobsRule


__all__ = ["NoTransferJobsRule"]