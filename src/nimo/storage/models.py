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
    model_version: Mapped[str] = mapped_column(String(40), default="1.0.0", nullable=False)
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


class SchemaMigration(Base):
    __tablename__ = "schema_migrations"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(80), default="local_user", nullable=False)
    object_type: Mapped[str | None] = mapped_column(String(80))
    object_id: Mapped[str | None] = mapped_column(String(120))
    details_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class BehaviourRun(Base):
    __tablename__ = "behaviour_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_data_version: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(40), default="1.0.0", nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="complete", nullable=False)
    diagnostics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class BehaviourPattern(Base):
    __tablename__ = "behaviour_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("behaviour_runs.id"), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scope_key: Mapped[str] = mapped_column(String(240), nullable=False, index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    periodic_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    spontaneous_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    distributional_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    pattern_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class BehaviouralMapRecord(Base):
    __tablename__ = "behavioural_maps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("behaviour_runs.id"), nullable=False, index=True)
    source_data_version: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    map_json: Mapped[str] = mapped_column(Text, nullable=False)
    archetype_label: Mapped[str] = mapped_column(String(240), nullable=False)
    archetype_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class TransactionOutlier(Base):
    __tablename__ = "transaction_outliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("behaviour_runs.id"), nullable=False, index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False, index=True)
    scope_key: Mapped[str] = mapped_column(String(240), nullable=False)
    robust_z: Mapped[float] = mapped_column(Float, nullable=False)
    surprise_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_outlier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class ForecastProfileRecord(Base):
    __tablename__ = "forecast_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), default="Default", nullable=False)
    source_behaviour_map_id: Mapped[int | None] = mapped_column(ForeignKey("behavioural_maps.id"))
    source_data_version: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    profile_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class ForecastScenarioRecord(Base):
    __tablename__ = "forecast_scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    profile_id: Mapped[int] = mapped_column(ForeignKey("forecast_profiles.id"), nullable=False)
    overrides_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    events_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class ForecastRunRecord(Base):
    __tablename__ = "forecast_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("forecast_scenarios.id"), nullable=False, index=True)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    horizon_months: Mapped[int] = mapped_column(Integer, nullable=False)
    simulation_runs: Mapped[int] = mapped_column(Integer, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_data_version: Mapped[str] = mapped_column(String(80), nullable=False)
    assumptions_json: Mapped[str] = mapped_column(Text, nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    paths_file: Mapped[str | None] = mapped_column(String(1024))
    calibration_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class BudgetRecord(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), default="category", nullable=False)
    period: Mapped[str] = mapped_column(String(32), default="monthly", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settings_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class BudgetLineRecord(Base):
    __tablename__ = "budget_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budgets.id"), nullable=False, index=True)
    category_slug: Mapped[str] = mapped_column(String(120), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="inferred", nullable=False)
    is_essential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settings_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class GoalRecord(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    current_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    monthly_contribution: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    surplus_allocation_fraction: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    settings_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class PortfolioRecord(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    allocations_json: Mapped[str] = mapped_column(Text, nullable=False)
    contribution_rule_json: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class InvestmentRunRecord(Base):
    __tablename__ = "investment_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    forecast_run_id: Mapped[int | None] = mapped_column(ForeignKey("forecast_runs.id"))
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    horizon_months: Mapped[int] = mapped_column(Integer, nullable=False)
    simulation_runs: Mapped[int] = mapped_column(Integer, nullable=False)
    stress_name: Mapped[str | None] = mapped_column(String(120))
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    paths_file: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ReportRunRecord(Base):
    __tablename__ = "report_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    provider: Mapped[str] = mapped_column(String(40), default="offline", nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    narrative_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_paths_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_data_version: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
