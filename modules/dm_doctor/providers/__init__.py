# File: modules/dm_doctor/providers/__init__.py
"""DM-Doctor EvidenceProviders. Providers collect evidence only (no diagnosis). """ 
from .dm_jobs_trace import DmJobsTraceProvider
__all__ = ["DmJobsTraceProvider"]
