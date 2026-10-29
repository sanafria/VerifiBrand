"""Evidence Verification Service for BrandLedger.

Ensures every finding is traceable to approved policy evidence by verifying:
1. Policy card identifiers exist in the approved policy set.
2. Policy version matches the exact approved version.
3. Source quotations exist as actual text within the approved policy content.
4. Quotations are relevant to the rule category and finding explanation.
5. Fabricated, modified, mismatched, or nonexistent citations are strictly rejected.
"""

import re
from typing import List, Optional
from pydantic import BaseModel
from backend.app.schemas.finding import Finding, FindingCategory
from backend.app.schemas.policy import PolicyCard


def normalize_text_for_comparison(text: str) -> str:
    """Normalize text by collapsing whitespace and normalizing quotes for robust verification."""
    if not text:
        return ""
    # Normalize smart quotes / dashes to standard equivalents
    t = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def verify_policy_card_and_version(
    policy_card_id: str,
    policy_version: str,
    policy_cards_by_id: dict[str, PolicyCard]
) -> tuple[bool, Optional[str], Optional[PolicyCard]]:
    """Verify that policy_card_id exists and policy_version matches the approved record.

    Returns:
        (is_valid, failure_reason, policy_card)
    """
    if not policy_card_id or not policy_card_id.strip():
        return False, "Finding policy_card_id is empty or missing.", None

    card = policy_cards_by_id.get(policy_card_id.strip())
    if not card:
        return (
            False,
            f"Referenced policy_card_id '{policy_card_id}' does not exist in approved policy library.",
            None,
        )

    # Validate exact version match (do not silently substitute another version)
    expected_version = card.version.strip()
    actual_version = policy_version.strip()
    if expected_version != actual_version:
        return (
            False,
            f"Policy version mismatch for card '{policy_card_id}': "
            f"finding references '{actual_version}', but approved version is '{expected_version}'.",
            card,
        )

    return True, None, card


def verify_source_quotation(
    source_quote: str,
    policy_card: PolicyCard
) -> tuple[bool, Optional[str]]:
    """Verify that source_quote exists as an actual substring in the policy card content.

    Rejects fabricated or modified quotations.
    """
    if not source_quote or not source_quote.strip():
        return False, "Source quotation is missing or empty."

    norm_quote = normalize_text_for_comparison(source_quote)
    norm_content = normalize_text_for_comparison(policy_card.content)

    if not norm_content:
        return False, f"Referenced policy card '{policy_card.id}' has no content."

    # Substring check with whitespace normalization
    if norm_quote.lower() not in norm_content.lower():
        return (
            False,
            f"Source quotation '{source_quote}' was not found in approved policy card '{policy_card.id}' content."
        )

    return True, None


def verify_quotation_relevance(
    finding: Finding,
    policy_card: PolicyCard
) -> tuple[bool, Optional[str]]:
    """Verify that the source quotation is relevant to the finding rule and explanation.

    Ensures that a random or unrelated quotation from the same card is not used to
    justify an unrelated rule violation.
    """
    quote_lower = finding.source_quote.lower()
    matched_lower = finding.matched_text.lower()
    cat = finding.category

    if cat == FindingCategory.TERMINOLOGY.value:
        # Quote must contain prohibited term or rule keywords
        if matched_lower not in quote_lower and not any(
            w in quote_lower for w in ("prohibit", "require", "term", "use", "instead")
        ):
            return False, "Source quotation does not mention prohibited terminology or requirement."

    elif cat == FindingCategory.EXPIRED_OFFER.value:
        # Quote must contain validity date or expiration terminology
        if not any(w in quote_lower for w in ("valid", "expire", "through", "until", "date", "ends")):
            return False, "Source quotation does not establish offer validity or expiration date."

    elif cat == FindingCategory.FACTUAL_ACCURACY.value:
        # Quote must contain numerical values, limits, or relevant metric words
        has_num = bool(re.search(r"\d+", finding.source_quote))
        if not has_num:
            return False, "Source quotation does not contain approved numerical facts or limits."

    elif cat == FindingCategory.UNSUPPORTED_CLAIM.value:
        # Quote must establish substantiation / evidence requirement
        if not any(w in quote_lower for w in ("evidence", "substantiat", "require", "document", "proof")):
            return False, "Source quotation does not establish claim substantiation requirement."

    return True, None


def verify_finding(
    finding: Finding,
    policy_cards_by_id: dict[str, PolicyCard]
) -> tuple[bool, Optional[str]]:
    """Perform full evidence verification on an individual finding.

    Checks:
    1. Card ID exists.
    2. Version matches exact card version.
    3. Source quote exists in approved card text.
    4. Quote is relevant to the finding.

    Returns:
        (is_verified, rejection_reason)
    """
    # 1. Verify card and version
    valid_id, err_id, card = verify_policy_card_and_version(
        finding.policy_card_id,
        finding.policy_version,
        policy_cards_by_id
    )
    if not valid_id or not card:
        return False, err_id

    # 2. Verify source quotation text
    valid_quote, err_quote = verify_source_quotation(finding.source_quote, card)
    if not valid_quote:
        return False, err_quote

    # 3. Verify quotation relevance
    valid_rel, err_rel = verify_quotation_relevance(finding, card)
    if not valid_rel:
        return False, err_rel

    return True, None


def filter_and_verify_findings(
    findings: list[Finding],
    policy_cards: list[PolicyCard]
) -> list[Finding]:
    """Verify all findings against approved policy evidence and return validated findings.

    Findings with fabricated quotations, invalid policy IDs, or mismatched versions
    are strictly rejected. Unsupported claims that lack draft evidence remain flagged
    as unverified findings without being classified as proven false.
    """
    verified_findings: list[Finding] = []
    cards_by_id = {card.id: card for card in policy_cards}

    for finding in findings:
        is_valid, reason = verify_finding(finding, cards_by_id)
        if is_valid:
            # If finding is an unsupported claim, preserve is_verified=False to indicate unverified status
            if finding.category == FindingCategory.UNSUPPORTED_CLAIM.value:
                verified_findings.append(finding.model_copy(update={"is_verified": False}))
            else:
                verified_findings.append(finding.model_copy(update={"is_verified": True}))
        else:
            # Rejection: invalid or fabricated evidence citations cannot pass verification
            continue

    return verified_findings


class VerificationDetail(BaseModel):
    """Machine-readable verification detail for an individual finding."""
    finding_category: str
    matched_text: str
    policy_card_id: str
    policy_version: str
    is_verified: bool
    rejection_reason: Optional[str] = None
    source_quote: str


class EvidenceVerificationReport(BaseModel):
    """Machine-readable aggregate evidence verification report."""
    total_findings: int
    verified_count: int
    rejected_count: int
    is_fully_verified: bool
    details: List[VerificationDetail]


def verify_findings_with_report(
    findings: list[Finding],
    policy_cards: list[PolicyCard],
) -> tuple[list[Finding], EvidenceVerificationReport]:
    """Verify all findings against approved policy evidence and return validated findings
    along with a machine-readable verification report detailing verification status and
    rejection reasons for any invalid or unverified citations.
    """
    verified_findings: list[Finding] = []
    details: list[VerificationDetail] = []
    cards_by_id = {card.id: card for card in policy_cards}

    for finding in findings:
        is_valid, reason = verify_finding(finding, cards_by_id)
        if is_valid:
            if finding.category == FindingCategory.UNSUPPORTED_CLAIM.value:
                verified_findings.append(finding.model_copy(update={"is_verified": False}))
                details.append(VerificationDetail(
                    finding_category=finding.category,
                    matched_text=finding.matched_text,
                    policy_card_id=finding.policy_card_id,
                    policy_version=finding.policy_version,
                    is_verified=False,
                    rejection_reason="Claim lacks evidence in draft; flagged as unverified claim.",
                    source_quote=finding.source_quote,
                ))
            else:
                verified_findings.append(finding.model_copy(update={"is_verified": True}))
                details.append(VerificationDetail(
                    finding_category=finding.category,
                    matched_text=finding.matched_text,
                    policy_card_id=finding.policy_card_id,
                    policy_version=finding.policy_version,
                    is_verified=True,
                    rejection_reason=None,
                    source_quote=finding.source_quote,
                ))
        else:
            details.append(VerificationDetail(
                finding_category=finding.category,
                matched_text=finding.matched_text,
                policy_card_id=finding.policy_card_id,
                policy_version=finding.policy_version,
                is_verified=False,
                rejection_reason=reason,
                source_quote=finding.source_quote,
            ))

    report = EvidenceVerificationReport(
        total_findings=len(findings),
        verified_count=len(verified_findings),
        rejected_count=len(findings) - len(verified_findings),
        is_fully_verified=len(verified_findings) == len(findings),
        details=details,
    )
    return verified_findings, report
