"""
PathoGuard-AI Database Package
"""

from app.db.database import get_db, get_connection
from app.db.repository import (
    init_db,
    save_assessment_record,
    get_assessment_record,
    list_assessment_records,
    delete_assessment_record,
    purge_user_records,
    compare_assessment_records,
    save_report_record,
    get_report_record,
    update_report_verification_record
)

__all__ = [
    "get_db",
    "get_connection",
    "init_db",
    "save_assessment_record",
    "get_assessment_record",
    "list_assessment_records",
    "delete_assessment_record",
    "purge_user_records",
    "compare_assessment_records",
    "save_report_record",
    "get_report_record",
    "update_report_verification_record"
]
