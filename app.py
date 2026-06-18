import csv
import io
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from typing import List, Union

import streamlit as st

from claim_extractor import extract_claims
from models import Verdict, Claim
from pdf_extractor import extract_text_from_pdf
from verifier import verify_claim
from web_searcher import search_claim

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_CLAIMS = 20

st.set_page_config(
    page_title="Fact Checker",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.verified { color: #1a7a4a; font-weight: 600; }
.inaccurate { color: #b85c00; font-weight: 600; }
.false { color: #b91c1c; font-weight: 600; }
.unverifiable { color: #6b7280; font-weight: 600; }

.metric-card {
    border: 1px solid rgba(128,128,128,0.2);
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
}

.metric-value {
    font-size: 2rem;
    font-weight: 700;
}

.metric-label {
    color: gray;
    font-size: 0.8rem;
}

.source-pill {
    display: inline-block;
    background: rgba(128,128,128,0.1);
    border-radius: 4px;
    padding: 2px 8px;
    margin: 2px;
    font-size: 0.75rem;
}
</style>
""", unsafe_allow_html=True)

STATUS_STYLE = {
    "Verified": ("✅", "verified"),
    "Inaccurate": ("⚠️", "inaccurate"),
    "False": ("❌", "false"),
    "Unverifiable": ("❓", "unverifiable"),
}


def render_metric(value: Union[int, str], label: str, color: str = "inherit") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value" style="color:{color}">
                {value}
            </div>
            <div class="metric-label">
                {label}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def process_claim(claim: Claim) -> Verdict:
    search_results = search_claim(claim)
    return verify_claim(claim, search_results)


def verdicts_to_csv(verdicts: List[Verdict]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Claim",
        "Status",
        "Confidence",
        "Corrected Fact",
        "Explanation",
        "Sources",
    ])

    for verdict in verdicts:
        sources = " | ".join(
            evidence.url for evidence in verdict.evidence_used
        )

        writer.writerow([
            verdict.claim.text,
            verdict.status,
            f"{verdict.confidence:.0%}",
            verdict.corrected_fact or "",
            verdict.explanation,
            sources,
        ])

    return output.getvalue()


def render_results(verdicts: List[Verdict]) -> None:

    total = len(verdicts)
    verified = sum(v.status == "Verified" for v in verdicts)
    inaccurate = sum(v.status == "Inaccurate" for v in verdicts)
    false = sum(v.status == "False" for v in verdicts)
    unverifiable = sum(v.status == "Unverifiable" for v in verdicts)

    st.subheader("Summary")

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        render_metric(total, "Total Claims")

    with c2:
        render_metric(verified, "Verified", "#1a7a4a")

    with c3:
        render_metric(inaccurate, "Inaccurate", "#b85c00")

    with c4:
        render_metric(false, "False", "#b91c1c")

    with c5:
        render_metric(unverifiable, "Unverifiable", "#6b7280")

    st.markdown("---")

    csv_data = verdicts_to_csv(verdicts)

    st.download_button(
        label="⬇ Download CSV",
        data=csv_data,
        file_name="fact_check_results.csv",
        mime="text/csv",
    )

    st.markdown("### Results")

    for verdict in verdicts:

        icon, css = STATUS_STYLE.get(
            verdict.status,
            ("❓", "unverifiable")
        )

        title = verdict.claim.text[:120]
        if len(verdict.claim.text) > 120:
            title += "..."

        with st.expander(f"{icon} {title}"):

            col1, col2 = st.columns([3, 1])

            with col1:

                st.markdown(
                    f"**Status:** "
                    f"<span class='{css}'>{icon} {verdict.status}</span>",
                    unsafe_allow_html=True,
                )

                st.markdown(
                    f"**Confidence:** {verdict.confidence:.0%}"
                )

                if verdict.corrected_fact:
                    st.info(
                        f"**Corrected Fact:** {verdict.corrected_fact}"
                    )

                st.markdown(
                    f"**Explanation:** {verdict.explanation}"
                )

                if verdict.claim.context:
                    st.caption(
                        f"📄 Context: {verdict.claim.context}"
                    )

            with col2:

                st.markdown("**Sources**")

                if verdict.evidence_used:

                    for evidence in verdict.evidence_used:

                        try:
                            domain = urlparse(
                                evidence.url
                            ).netloc
                        except Exception:
                            domain = evidence.url

                        date_text = (
                            f" · {evidence.published_date}"
                            if evidence.published_date
                            else ""
                        )

                        st.markdown(
                            f'<a href="{evidence.url}" '
                            f'target="_blank" '
                            f'class="source-pill">'
                            f'{domain}{date_text}</a>',
                            unsafe_allow_html=True,
                        )

                else:
                    st.caption("No sources found.")


def main() -> None:

    st.title("🔍 Fact Checker")

    st.caption(
        "Upload a PDF and verify factual claims against live web data."
    )

    st.markdown("---")

    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
    )

    if not uploaded_file:
        st.info("Upload a PDF to begin.")
        return

    if st.button("🔎 Analyze", type="primary"):

        start_time = time.time()

        with st.status(
            "Running fact-check pipeline...",
            expanded=True,
        ) as status:

            st.write("📄 Extracting PDF text...")

            pdf_text = extract_text_from_pdf(uploaded_file)

            st.write("PDF Text Preview:")
            st.text(pdf_text[:1000])

            if not pdf_text:
                st.error("Could not extract text from PDF.")
                status.update(
                    label="Failed",
                    state="error",
                )
                return

            st.write("🧠 Extracting claims...")

            claims = extract_claims(pdf_text)

            if not claims:
                st.warning("No factual claims found.")
                status.update(
                    label="No claims found",
                    state="complete",
                )
                return

            if len(claims) > MAX_CLAIMS:
                st.warning(
                    f"Found {len(claims)} claims. "
                    f"Processing first {MAX_CLAIMS}."
                )
                claims = claims[:MAX_CLAIMS]

            st.write(
                f"🌐 Verifying {len(claims)} claims..."
            )

            verdicts: List[Union[Verdict, None]] = [None] * len(claims)

            progress = st.progress(0)

            with ThreadPoolExecutor(
                max_workers=min(5, len(claims))
            ) as executor:

                future_to_index = {
                    executor.submit(
                        process_claim,
                        claim
                    ): idx
                    for idx, claim in enumerate(claims)
                }

                completed = 0

                for future in as_completed(future_to_index):

                    idx = future_to_index[future]

                    try:
                        verdicts[idx] = future.result()

                    except Exception as e:
                        logger.exception(
                            "Verification failed for claim index %s: %s",
                            idx,
                            e,
                        )

                    completed += 1

                    progress.progress(
                        completed / max(len(claims), 1)
                    )

            verdicts = [
                v for v in verdicts
                if v is not None
            ]

            severity_order = {
                "False": 0,
                "Inaccurate": 1,
                "Unverifiable": 2,
                "Verified": 3,
            }

            verdicts.sort(
                key=lambda v: severity_order.get(
                    v.status,
                    99,
                )
            )

            status.update(
                label="✅ Complete",
                state="complete",
                expanded=False,
            )

        elapsed = time.time() - start_time

        st.success(
            f"Completed in {elapsed:.1f} seconds"
        )

        if verdicts:
            render_results(verdicts)
        else:
            st.error(
                "All claim verifications failed."
            )


if __name__ == "__main__":
    main()

