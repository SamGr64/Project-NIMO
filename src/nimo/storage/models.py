from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), default="imported", nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="GBP", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    bank_name: Mapped[str | None] = mapped_column(String(160))
    account_number: Mapped[str | None] = mapped_column(String(80))
    sort_code: Mapped[str | None] = mapped_column(String(32))
    account_type: Mapped[str] = mapped_column(String(64), default="current", nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="GBP", nullable=False)
    opening_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")
    source_files: Mapped[list["SourceFile"]] = relationship(back_populates="account")


class SourceFile(Base):
    __tablename__ = "source_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    original_name: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    coverage_start: Mapped[date] = mapped_column(Date, nullable=False)
    coverage_end: Mapped[date] = mapped_column(Date, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    importer_version: Mapped[str] = mapped_column(String(32), default="1", nullable=False)
    mapping_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    warnings_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    account: Mapped[Account] = relationship(back_populates="source_files")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="source_file", foreign_keys="Transaction.source_file_id"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    direction: Mapped[str] = mapped_column(String(16), default="either", nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_account_date_active", "account_id", "booking_date", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_uid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    source_file_id: Mapped[int] = mapped_column(ForeignKey("source_files.id"), nullable=False, index=True)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    booking_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    value_date: Mapped[date | None] = mapped_column(Date)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    merchant_normalised: Mapped[str | None] = mapped_column(String(260), index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="GBP", nullable=False)
    running_balance: Mapped[float | None] = mapped_column(Float)
    external_reference: Mapped[str | None] = mapped_column(String(240))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    category_source: Mapped[str | None] = mapped_column(String(32))
    category_confidence: Mapped[float | None] = mapped_column(Float)
    transfer_group_id: Mapped[str | None] = mapped_column(String(36), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    superseded_by_source_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_files.id"), nullable=True
    )
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    account: Mapped[Account] = relationship(back_populates="transactions")
    source_file: Mapped[SourceFile] = relationship(
        back_populates="transactions", foreign_keys=[source_file_id]
    )
    category: Mapped[Category | None] = relationship()


class CategoryRule(Base):
    __tablename__ = "category_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    pattern: Mapped[str] = mapped_column(String(500), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    field: Mapped[str] = mapped_column(String(32), default="description", nullable=False)
    is_regex: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    category: Mapped[Category] = relationship()


class TransferMatch(Base):
    __tablename__ = "transfer_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    debit_transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False)
    credit_transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    date_gap_days: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_rejected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_data_version: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), default="0.5.0", nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="complete", nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class DashboardLayout(Base):
    __tablename__ = "dashboard_layouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    layout_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
