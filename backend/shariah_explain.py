"""Build the citation-backed explanation of a Shariah screening verdict.

This is the backend half of the dashboard's Shariah Trace panel: verdict -> which
rule fired -> the fiqh basis -> the citation. It explains a decision that has
already been made deterministically by sec_edgar_screen; it never makes one.
The rule from explain_compliance.py holds here too:

    External NON_COMPLIANT, ERROR, or UNKNOWN results remain rejected;
    notes explain but cannot override.

Every string in FIQH_BASIS is fixed text keyed by the rule that fired. Nothing here
is generated, inferred, or model-written -- CLAUDE.md permits a model to explain a
gate decision, and this module is what a model would be explaining.

Citation honesty: the policy notes under docs/shariah-policy/ are secondary
summaries of Usmani and Visser, not primary AAOIFI standard text. Every citation
carries `kind` so the UI can say so rather than overclaiming. Upgrading these to
primary sources is tracked in the hackathon research notes.
"""

from datetime import datetime, timezone

from sec_edgar_screen import MAX_RATIO_PCT, check_us_symbol

# The decision rule this module operates under, surfaced in the payload so the UI
# cannot present an explanation as though it were a second opinion.
DECISION_RULE = (
    "External NON_COMPLIANT, UNKNOWN, or ERROR results remain rejected; "
    "notes explain but cannot override."
)

METHODOLOGY_LABEL = "Securities Commission Malaysia, Shariah Advisory Council (SC/SAC)"

# Known approximations in the screen itself. Both err toward rejection, which is why
# they are acceptable -- but a judge or a scholar should see them stated.
LIMITATIONS = [
    "Business activity is approximated by the company's single SEC SIC code, which is "
    "one primary-industry label and cannot see a secondary non-compliant revenue line.",
    "XBRL does not distinguish Islamic instruments from conventional ones, so both "
    "ratios count sukuk and Islamic deposits as conventional and are overstated.",
    "Ratios anchor on the latest annual filing, so they lag the current balance sheet.",
]

CITATIONS = {
    "sc_activity": {
        "source": "docs/shariah-policy/screening-criteria-breakdown.md",
        "section": "1. Business Activity Exclusions (automatic disqualifiers)",
        "quote": (
            "Regardless of financial ratios, primary business in these activities "
            "disqualifies a company outright"
        ),
        "kind": "regulatory_methodology",
    },
    "sc_ratios": {
        "source": "docs/shariah-policy/screening-criteria-breakdown.md",
        "section": "2. Financial Ratio Benchmarks (exact numbers)",
        "quote": (
            "Each ratio, which is intended to measure riba and riba-based elements "
            "within a company's statements of financial position, must be less than 33%."
        ),
        "kind": "regulatory_methodology",
    },
    "sc_debt": {
        "source": "docs/shariah-policy/screening-criteria-breakdown.md",
        "section": "2. Financial Ratio Benchmarks - Debt over total assets",
        "quote": (
            "Debt only includes interest-bearing debt whereas Islamic financing or "
            "sukuk is excluded from the calculation."
        ),
        "kind": "regulatory_methodology",
    },
    "sc_cash": {
        "source": "docs/shariah-policy/screening-criteria-breakdown.md",
        "section": "2. Financial Ratio Benchmarks - Cash over total assets",
        "quote": (
            "Cash only includes cash placed in conventional accounts and instruments, "
            "whereas cash placed in Islamic accounts and instruments is excluded "
            "from the calculation."
        ),
        "kind": "regulatory_methodology",
    },
    "riba": {
        "source": "docs/shariah-policy/Riba.md",
        "work": "Usmani, Introduction to Islamic Finance; Visser, Islamic Finance: Principles and Practice",
        "quote": (
            "riba refers to the charging or paying of interest on loans... strictly "
            "forbidden (haram) because it guarantees an unearned, risk-free profit"
        ),
        "kind": "secondary_summary",
    },
    "equity_ownership": {
        "source": "docs/shariah-policy/Equity-stock-ownership.md",
        "kind": "secondary_summary",
    },
}

# principle -> claim -> citation, keyed by which rule fired. Fixed text, never generated.
FIQH_BASIS = {
    "business_activity": [
        {
            "principle": "Business activity exclusion",
            "claim": (
                "A company whose primary business is itself impermissible cannot be "
                "cured by a healthy balance sheet, so no ratio is computed. A "
                "conventional bank passes the ratio tests on its own balance sheet - "
                "running them first would give the wrong answer."
            ),
            "citation": CITATIONS["sc_activity"],
        },
    ],
    "financial_ratios": [
        {
            "principle": "Riba",
            "claim": (
                "Interest-bearing debt and conventional interest-bearing deposits are "
                "the two balance-sheet channels through which riba enters an otherwise "
                "permissible business. The SAC caps each at a strict 33% of total assets."
            ),
            "citation": CITATIONS["sc_ratios"],
        },
        {
            "principle": "Riba al-Nasiyah",
            "claim": (
                "Interest on borrowing is a predetermined, guaranteed increase over "
                "principal in return for deferral - the core prohibited mechanism."
            ),
            "citation": CITATIONS["riba"],
        },
        {
            "principle": "Equity ownership",
            "claim": (
                "Share ownership is permissible in the first place because the "
                "shareholder bears genuine ownership risk in a real business."
            ),
            "citation": CITATIONS["equity_ownership"],
        },
    ],
}

TRADEABLE_STATUSES = {"COMPLIANT"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ratio_tests(ratios: dict) -> list[dict]:
    """One entry per quantitative test, with the margin to the limit as evidence.

    Margin rather than a traffic light: NEXT_STEPS.md forbids compressing this into
    a colour on the pre-purchase surface, because a colour implies permission and
    the binary verdict is the only thing that grants it.
    """
    tests = []
    for name, key, citation_key, label in [
        ("interest_bearing_debt_ratio", "debt_ratio_pct", "sc_debt", "interest-bearing debt / total assets"),
        ("conventional_cash_ratio", "cash_ratio_pct", "sc_cash", "conventional cash / total assets"),
    ]:
        value = ratios.get(key)
        if value is None:
            continue
        limit = float(ratios.get("limit_pct") or MAX_RATIO_PCT)
        tests.append(
            {
                "name": name,
                "label": label,
                "value_pct": round(float(value), 4),
                "limit_pct": limit,
                "comparator": "<",
                "passed": float(value) < limit,
                "margin_pct": round(limit - float(value), 4),
                "citation": CITATIONS[citation_key],
            }
        )
    return tests


def explain_symbol(symbol: str, *, screen=None) -> dict:
    """Return verdict -> rule fired -> fiqh basis -> citation for one US symbol.

    `screen` replaces the screening call in tests, so nothing here reaches SEC.
    """
    normalized = str(symbol or "").strip().upper()
    if not normalized:
        return {
            "symbol": "",
            "as_of": _utc_now(),
            "company": None,
            "exchange": None,
            "verdict": {"status": "ERROR", "tradeable": False, "statement": "no symbol supplied"},
            "rule": None,
            "fiqh_basis": [],
            "evidence": {},
            "provenance": {"limitations": LIMITATIONS},
            "decision_rule": DECISION_RULE,
        }

    result = (screen or check_us_symbol)(normalized)
    status = str(result.get("status") or "UNKNOWN").upper()
    tier_name = result.get("screen")

    payload = {
        "symbol": normalized,
        "as_of": _utc_now(),
        "company": result.get("company"),
        "exchange": result.get("exchange"),
        "verdict": {
            "status": status,
            # The binary buy-gate answer, stated as such. Anything that is not
            # COMPLIANT -- including UNKNOWN and ERROR -- is not tradeable.
            "tradeable": status in TRADEABLE_STATUSES,
            "statement": result.get("reason"),
        },
        "rule": None,
        "fiqh_basis": FIQH_BASIS.get(tier_name, []),
        "evidence": {},
        "provenance": {
            "provider": result.get("provider"),
            "methodology": result.get("methodology"),
            "methodology_label": METHODOLOGY_LABEL,
            "report_date": result.get("report_date"),
            "screened_at": _utc_now(),
            "limitations": LIMITATIONS,
        },
        "decision_rule": DECISION_RULE,
    }

    if tier_name == "business_activity":
        payload["rule"] = {
            "id": "sc_my_sac.business_activity",
            "tier": 1,
            "tier_name": "business_activity",
            "label": "SC/SAC business-activity exclusion",
            "fired": result.get("reason"),
            "tests": [],
            "narrowest_margin_pct": None,
        }
        return payload

    if tier_name == "financial_ratios":
        ratios = result.get("ratios") or {}
        tests = _ratio_tests(ratios)
        margins = [test["margin_pct"] for test in tests]
        payload["rule"] = {
            "id": "sc_my_sac.financial_ratios",
            "tier": 2,
            "tier_name": "financial_ratios",
            "label": "SC/SAC financial-ratio screen",
            "fired": result.get("reason"),
            "tests": tests,
            # The tightest test is what a watcher cares about; TSLA sits one point
            # from failing on cash and that should be visible without a colour.
            "narrowest_margin_pct": round(min(margins), 4) if margins else None,
        }
        payload["evidence"] = {
            "filing": {
                "form": ratios.get("form"),
                "report_date": ratios.get("report_date"),
                "total_assets": ratios.get("total_assets"),
            },
            "interest_bearing_debt": {
                "value": ratios.get("interest_bearing_debt"),
                "xbrl_concepts": ratios.get("debt_concepts_used") or [],
            },
            "conventional_cash": {
                "value": ratios.get("conventional_cash"),
                "xbrl_concepts": ratios.get("cash_concepts_used") or [],
            },
        }
        return payload

    # UNKNOWN / ERROR: no rule fired, and the verdict is already not tradeable.
    payload["rule"] = {
        "id": "sc_my_sac.indeterminate",
        "tier": None,
        "tier_name": tier_name,
        "label": "screen could not reach a verdict",
        "fired": result.get("reason"),
        "tests": [],
        "narrowest_margin_pct": None,
    }
    return payload
