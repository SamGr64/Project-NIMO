#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "architecture"

PALETTE = {
    "blue": ("#DAE8FC", "#6C8EBF"),
    "green": ("#D5E8D4", "#82B366"),
    "purple": ("#E1D5E7", "#9673A6"),
    "yellow": ("#FFF2CC", "#D6B656"),
    "red": ("#F8CECC", "#B85450"),
    "grey": ("#F5F5F5", "#666666"),
    "orange": ("#FFE6CC", "#D79B00"),
}


def diagram(filename: str, title: str, nodes: list[dict], edges: list[tuple[str, str, str | None]], *, width: int = 1600, height: int = 900) -> None:
    mxfile = ET.Element(
        "mxfile",
        {
            "host": "app.diagrams.net",
            "modified": datetime.now(timezone.utc).isoformat(),
            "agent": "Project NIMO 1.0 architecture generator",
            "version": "26.0.0",
            "type": "device",
        },
    )
    d = ET.SubElement(mxfile, "diagram", {"id": filename.removesuffix(".drawio"), "name": title})
    model = ET.SubElement(
        d,
        "mxGraphModel",
        {
            "dx": str(width), "dy": str(height), "grid": "1", "gridSize": "10", "guides": "1",
            "tooltips": "1", "connect": "1", "arrows": "1", "fold": "1", "page": "1",
            "pageScale": "1", "pageWidth": str(width), "pageHeight": str(height), "math": "0", "shadow": "0",
        },
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    title_cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": "title", "value": f"<b>{title}</b>", "vertex": "1", "parent": "1",
            "style": "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;fontSize=24;fontStyle=1;",
        },
    )
    ET.SubElement(title_cell, "mxGeometry", {"x": "40", "y": "20", "width": str(width - 80), "height": "45", "as": "geometry"})
    for node in nodes:
        fill, stroke = PALETTE[node.get("colour", "blue")]
        style = (
            "rounded=1;whiteSpace=wrap;html=1;"
            f"fillColor={fill};strokeColor={stroke};fontSize={node.get('font', 13)};"
            "fontFamily=Helvetica;align=center;verticalAlign=middle;spacing=8;"
        )
        cell = ET.SubElement(
            root,
            "mxCell",
            {"id": node["id"], "value": node["value"], "style": style, "vertex": "1", "parent": "1"},
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {"x": str(node["x"]), "y": str(node["y"]), "width": str(node["w"]), "height": str(node["h"]), "as": "geometry"},
        )
    for index, (source, target, label) in enumerate(edges, 1):
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": f"edge{index}", "value": label or "", "edge": "1", "parent": "1", "source": source, "target": target,
                "style": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;strokeWidth=2;fontSize=11;",
            },
        )
        ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    ET.indent(mxfile, space="  ")
    ET.ElementTree(mxfile).write(OUT / filename, encoding="utf-8", xml_declaration=True)


def box(node_id: str, value: str, x: int, y: int, w: int, h: int, colour: str = "blue", font: int = 13) -> dict:
    return {"id": node_id, "value": value, "x": x, "y": y, "w": w, "h": h, "colour": colour, "font": font}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    diagram(
        "system_context.drawio",
        "Project NIMO 1.0 — System Context",
        [
            box("user", "<b>User</b><br>statements, assumptions, goals,<br>budgets, portfolios and layouts", 50, 170, 250, 125, "yellow"),
            box("cli", "<b>CLI</b><br>complete bare-bones interface", 370, 100, 240, 85),
            box("dash", "<b>Streamlit dashboard</b><br>pages, widgets and themes", 370, 250, 240, 85),
            box("services", "<b>Application services</b><br>shared use-case boundary", 700, 170, 260, 110, "green"),
            box("data", "Generation + ingestion<br>categories + transfers", 1060, 80, 230, 95, "purple"),
            box("models", "Analysis + behaviour<br>forecasting + planning", 1060, 205, 230, 95, "purple"),
            box("outputs", "Investing + reporting<br>backup + diagnostics", 1060, 330, 230, 95, "purple"),
            box("db", "<b>Per-user SQLite</b><br>canonical data, models,<br>scenarios and provenance", 680, 470, 300, 125, "red"),
            box("files", "<b>User workspace files</b><br>raw / synthetic / exports<br>reports / cache", 1060, 500, 260, 110, "red"),
            box("openai", "Optional OpenAI provider<br>structured narrative only", 350, 610, 260, 90, "grey"),
            box("market", "Market provider interface<br>local synthetic data by default", 350, 740, 260, 90, "grey"),
            box("trust", "<b>Trust boundary</b><br>hidden generator truth never enters analysis;<br>LLM cannot recalculate results;<br>sandbox cannot place trades", 740, 690, 520, 125, "orange"),
        ],
        [
            ("user", "cli", None), ("user", "dash", None), ("cli", "services", None), ("dash", "services", None),
            ("services", "data", None), ("services", "models", None), ("services", "outputs", None),
            ("data", "db", None), ("models", "db", None), ("outputs", "db", None),
            ("data", "files", None), ("outputs", "files", None),
            ("outputs", "openai", "optional"), ("outputs", "market", "provider"),
            ("db", "trust", "local-first"), ("files", "trust", "sensitive"),
        ],
    )

    diagram(
        "process_flow.drawio",
        "Project NIMO 1.0 — End-to-End Process Flow",
        [
            box("input", "<b>Input</b><br>real CSV OR seed/date/archetype/questionnaire", 45, 130, 240, 105, "yellow"),
            box("statements", "Rendered/imported statements", 340, 130, 220, 80),
            box("normal", "<b>Normalisation</b><br>account/date overlap supersession<br>without row equality deduplication", 620, 110, 270, 120, "green"),
            box("db", "Canonical per-user database", 965, 130, 235, 80, "red"),
            box("desc", "Descriptive analysis<br>categories + transfers + cash flow", 1260, 105, 250, 130, "purple"),
            box("beh", "<b>Behavioural map</b><br>periodic / distributional / spontaneous", 1260, 320, 250, 105, "purple"),
            box("forecast", "<b>Default forecast</b><br>assumptions + Monte Carlo", 930, 330, 260, 100, "blue"),
            box("userplan", "User scenarios<br>overrides + future events", 610, 330, 240, 100, "yellow"),
            box("budget", "Budgets + goals<br>probabilities + interventions", 260, 310, 250, 110, "green"),
            box("invest", "Investing sandbox<br>contributions + stress tests", 260, 500, 250, 105, "green"),
            box("evidence", "Frozen structured evidence", 610, 530, 240, 80, "orange"),
            box("narrative", "Offline or optional<br>schema-validated LLM narrative", 930, 520, 260, 100, "grey"),
            box("report", "HTML / Markdown / PDF / DOCX", 1260, 530, 250, 90, "red"),
            box("hardening", "Migrations • audit • doctor<br>portable/encrypted backup • CI", 610, 710, 580, 90, "grey"),
        ],
        [
            ("input", "statements", None), ("statements", "normal", None), ("normal", "db", None), ("db", "desc", None),
            ("desc", "beh", None), ("beh", "forecast", None), ("forecast", "userplan", "editable"),
            ("userplan", "budget", None), ("forecast", "budget", None), ("budget", "invest", "surplus"),
            ("forecast", "invest", "cash paths"), ("budget", "evidence", None), ("invest", "evidence", None),
            ("beh", "evidence", None), ("forecast", "evidence", None), ("evidence", "narrative", None),
            ("narrative", "report", None), ("db", "hardening", None), ("report", "hardening", None),
        ],
    )

    diagram(
        "data_model.drawio",
        "Project NIMO 1.0 — Logical Data Model",
        [
            box("user", "<b>User</b>", 70, 95, 180, 65, "yellow"),
            box("account", "Accounts", 70, 220, 180, 65, "blue"),
            box("source", "Source files<br>hash + date coverage", 330, 105, 220, 85, "blue"),
            box("txn", "<b>Transactions</b><br>active/superseded + provenance", 330, 240, 240, 100, "red"),
            box("category", "Categories + rules", 70, 370, 200, 75, "green"),
            box("transfer", "Transfer matches", 330, 390, 220, 75, "green"),
            box("beh_run", "Behaviour runs<br>patterns + outliers", 660, 100, 240, 95, "purple"),
            box("beh_map", "Behavioural maps<br>archetype summary", 660, 245, 240, 90, "purple"),
            box("profile", "Forecast profiles", 990, 95, 220, 75, "blue"),
            box("scenario", "Forecast scenarios<br>overrides + events", 990, 220, 220, 90, "blue"),
            box("frun", "Forecast runs<br>summary + path cache", 990, 365, 220, 90, "blue"),
            box("budget", "Budgets + lines", 1320, 95, 200, 75, "green"),
            box("goal", "Goals", 1320, 220, 200, 70, "green"),
            box("portfolio", "Portfolios", 1320, 345, 200, 70, "orange"),
            box("irun", "Investment runs", 1320, 460, 200, 75, "orange"),
            box("report", "Report runs<br>evidence + narrative + outputs", 930, 575, 280, 100, "red"),
            box("layout", "Dashboard layouts", 590, 575, 240, 75, "grey"),
            box("hard", "Migrations + audit", 270, 575, 220, 75, "grey"),
        ],
        [
            ("user", "account", "1:n"), ("account", "txn", "1:n"), ("source", "txn", "1:n"),
            ("category", "txn", "classifies"), ("txn", "transfer", "paired"), ("txn", "beh_run", "input"),
            ("beh_run", "beh_map", "produces"), ("beh_map", "profile", "builds"), ("profile", "scenario", "1:n"),
            ("scenario", "frun", "1:n"), ("scenario", "budget", "evaluates"), ("scenario", "goal", "simulates"),
            ("scenario", "portfolio", "cash path"), ("portfolio", "irun", "1:n"), ("frun", "report", "evidence"),
            ("budget", "report", "evidence"), ("goal", "report", "evidence"), ("irun", "report", "evidence"),
            ("user", "layout", "1:n"), ("user", "hard", "ledger"),
        ],
    )

    phases = []
    x_positions = [45, 300, 555, 810, 1065, 1320]
    first = [
        ("p0", "<b>Phase 0</b><br>foundation + services"), ("p1", "<b>Phase 1</b><br>database + import"),
        ("p2", "<b>Phase 2</b><br>seeded generator"), ("p3", "<b>Phase 3</b><br>metrics + CLI"),
        ("p4", "<b>Phase 4</b><br>dashboard + layouts"), ("p5", "<b>Phase 5</b><br>categories + cash flow"),
    ]
    for (node_id, label), x in zip(first, x_positions):
        phases.append(box(node_id, f"{label}<br><b>COMPLETE</b>", x, 120, 220, 100, "green"))
    second = [
        ("p6", "<b>Phase 6</b><br>behaviour inference"), ("p7", "<b>Phase 7</b><br>forecasting + scenarios"),
        ("p8", "<b>Phase 8</b><br>budgets + goals"), ("p9", "<b>Phase 9</b><br>reports + advice"),
        ("p10", "<b>Phase 10</b><br>investing sandbox"), ("p11", "<b>Phase 11</b><br>hardening + release"),
    ]
    for (node_id, label), x in zip(second, x_positions):
        phases.append(box(node_id, f"{label}<br><b>COMPLETE BASELINE</b>", x, 390, 220, 105, "green"))
    phases.append(box("future", "<b>Post-1.0 themes</b><br>calibration • additional importers • stronger models • authenticated deployment", 360, 650, 880, 105, "blue"))
    roadmap_edges = [(f"p{i}", f"p{i+1}", None) for i in range(11)] + [("p11", "future", None)]
    diagram("phase_roadmap.drawio", "Project NIMO 1.0 — Delivery Roadmap", phases, roadmap_edges)

    diagram(
        "behaviour_forecasting_loop.drawio",
        "Behaviour Discovery and Forecasting Loop",
        [
            box("truth", "Hidden synthetic truth<br><i>generator/benchmark only</i>", 70, 120, 240, 100, "red"),
            box("tx", "Observable transactions", 400, 120, 220, 80, "blue"),
            box("features", "Timing • amount • category<br>merchant • account • transfers", 710, 110, 250, 100, "purple"),
            box("map", "<b>Behavioural map</b><br>periodic / distributional / spontaneous", 1060, 105, 300, 110, "green"),
            box("profile", "Default forecast profile<br>assumptions + provenance", 1060, 340, 300, 100, "blue"),
            box("scenario", "User scenario<br>overrides + events", 710, 345, 250, 90, "yellow"),
            box("mc", "Monte Carlo future paths", 400, 350, 220, 80, "purple"),
            box("out", "Intervals • threshold probabilities<br>category paths • backtest diagnostics", 70, 335, 250, 110, "green"),
            box("benchmark", "Recovery benchmark compares<br>truth ↔ inferred map<br><b>outside production inference</b>", 520, 600, 420, 110, "orange"),
        ],
        [
            ("truth", "tx", "generates"), ("tx", "features", None), ("features", "map", None),
            ("map", "profile", None), ("profile", "scenario", "copy/override"), ("scenario", "mc", None),
            ("mc", "out", None), ("truth", "benchmark", "test only"), ("map", "benchmark", "test only"),
        ],
    )

    diagram(
        "planning_investing_flow.drawio",
        "Planning and Educational Investing Flow",
        [
            box("forecast", "Forecast cash-flow paths", 70, 120, 230, 85, "blue"),
            box("budget", "Inferred/default budget", 390, 90, 230, 80, "green"),
            box("custom", "User budget overrides", 390, 230, 230, 80, "yellow"),
            box("goals", "Goals<br>target + date + allocation", 710, 90, 240, 95, "green"),
            box("intervene", "Intervention comparison<br>change category behaviour", 710, 245, 240, 95, "purple"),
            box("capacity", "Investable capacity<br>after cash floor and goals", 1040, 145, 250, 105, "orange"),
            box("portfolio", "Portfolio + contribution rule", 1040, 340, 250, 90, "yellow"),
            box("market", "Synthetic educational<br>joint return history", 710, 520, 240, 90, "grey"),
            box("sim", "Combined cash + portfolio<br>Monte Carlo simulation", 1040, 520, 250, 95, "purple"),
            box("results", "Liquidity • goal effect • ranges<br>contributions • drawdown • stress", 1350, 320, 210, 120, "green"),
            box("notice", "No trade execution<br>No guaranteed forecast<br>No product recommendation", 1300, 560, 260, 100, "red"),
        ],
        [
            ("forecast", "budget", None), ("budget", "custom", None), ("custom", "goals", None),
            ("forecast", "goals", None), ("goals", "intervene", None), ("goals", "capacity", None),
            ("forecast", "capacity", None), ("capacity", "portfolio", None), ("portfolio", "sim", None),
            ("forecast", "sim", "cash paths"), ("market", "sim", "return paths"), ("sim", "results", None),
            ("results", "notice", "educational boundary"),
        ],
    )

    diagram(
        "reporting_security_flow.drawio",
        "Reporting, Privacy and Backup Boundaries",
        [
            box("db", "Per-user database", 60, 120, 220, 80, "red"),
            box("evidence", "<b>Structured evidence builder</b><br>facts • inference • assumptions • projections", 380, 95, 300, 125, "orange"),
            box("offline", "Offline narrative provider", 800, 80, 230, 75, "green"),
            box("llm", "Optional OpenAI provider<br>schema-validated narrative", 800, 210, 230, 90, "grey"),
            box("schema", "ReportNarrative schema", 1110, 140, 220, 75, "blue"),
            box("render", "NIMO renderers<br>HTML • MD • PDF • DOCX", 1380, 120, 180, 110, "purple"),
            box("workspace", "Workspace files<br>raw • reports • cache", 60, 430, 220, 90, "red"),
            box("snapshot", "Consistent SQLite snapshot<br>portable path normalisation", 380, 415, 300, 105, "blue"),
            box("manifest", "SHA-256 backup manifest", 800, 410, 230, 80, "green"),
            box("encrypt", "Optional PBKDF2 + Fernet<br>.nimoenc", 1110, 405, 220, 90, "grey"),
            box("restore", "Verify • safe extract • recreate dirs<br>migrate • doctor", 1380, 405, 180, 110, "orange"),
            box("boundary", "<b>Privacy rules</b><br>offline by default • raw descriptions excluded • no secrets in config • caches optional", 470, 670, 650, 105, "yellow"),
        ],
        [
            ("db", "evidence", None), ("evidence", "offline", "default"), ("evidence", "llm", "opt-in"),
            ("offline", "schema", None), ("llm", "schema", None), ("schema", "render", None),
            ("workspace", "snapshot", None), ("db", "snapshot", None), ("snapshot", "manifest", None),
            ("manifest", "encrypt", "optional"), ("encrypt", "restore", None), ("manifest", "restore", "plain ZIP"),
            ("evidence", "boundary", None), ("snapshot", "boundary", None),
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
