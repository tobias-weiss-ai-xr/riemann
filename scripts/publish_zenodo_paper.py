#!/usr/bin/env python3
"""
Zenodo publish: Upload comprehensive paper to Zenodo using Playwright.
Uses session cookies to avoid token setup.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright

BASE_URL = "https://zenodo.org"
PAPER_PATH = "C:/Users/Tobias/git/next-tobias-weiss-org/machine-learning-modular-forms-comprehensive.md"


async def publish_to_zenodo():
    """Create zenodo deposit, upload paper, fill metadata, publish."""
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)  # Show for debugging
        context = await browser.new_context()

        # Navigate to Zenodo login page
        page = await context.new_page()
        await page.goto(f"{BASE_URL}/login")

        # Check if already logged in or need to login
        login_form = await page.query_selector("form[action*='/login']")
        if login_form:
            print("Please login to Zenodo in the browser...")
            # Wait for user to login manually
            await page.wait_for_url(f"{BASE_URL}/", timeout=300000)  # 5 min timeout
            print("Login detected!")
        else:
            print("Already logged in or different page")

        # Navigate to new upload
        await page.goto(f"{BASE_URL}/uploads/new")

        # Wait for upload form to appear
        await page.wait_for_selector("input[type='file']", timeout=30000)

        # Upload the paper
        print("Uploading paper...")
        file_input = await page.query_selector("input[type='file']")

        # Workaround for Playwright .fill() issue with React Hook Form
        await page.evaluate(f"""(filePath) => {{
            const input = document.querySelector('input[type="file"]');
            const dt = new DataTransfer();
            const file = new File([''], '{Path(PAPER_PATH).name}', {{ type: 'text/markdown' }});
            dt.items.add(file);
            input.files = dt.files;
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}""")

        # Alternative: Use native file upload if .fill() doesn't work
        await file_input.set_input_files(PAPER_PATH)

        print("Waiting for upload to complete...")
        await page.wait_for_timeout(5000)

        # Fill in metadata using React Hook Form workaround
        print("Filling metadata...")

        # Title
        title = "Machine Learning for Modular Forms: Hecke Traces, L-Function Zeros, and the Sato-Tate Distribution"
        await page.evaluate(f"""(val) => {{
            const input = document.querySelector('input[name="metadata.title"]');
            if (input) {{
                Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, val);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        }}""", title)

        # Description (abstract)
        abstract = """We present a comprehensive data-driven investigation into the relationship between Hecke trace sequences of modular forms and their number-theoretic invariants. Starting from systematically failed graph neural network (GNN) experiments on Cayley graphs of SL(2,F_p), we pivot to a data-scaling approach, collecting 200,000 weight-2 newforms from the LMFDB database with 100 Hecke trace coefficients each. Standard machine learning models achieve state-of-the-art results: analytic rank classification F1 = 0.970, dimension regression R² = 0.990, and CM form detection F1 = 0.919.

A trace-index graph construction - connecting newforms via shared Chef eigenstructure - enables a ChebConv GNN to predict the first L-function zero with R² = 0.631, outperforming the tabular baseline by 20%. An architecture search reveals GATConv achieves R² = 0.731, a 15.9% improvement via learned attention over structural edges. A stacked ensemble refines ChebConv to R² = 0.656.

We validate Sato-Tate predictions on 53K LMFDB newforms, confirming the SU(2) distribution (moment errors <1e-3) and identifying CM forms via a divisive mean formula M4/M2² at F1 = 0.919. Connes' colored vanishing spectrum (CvS) operator theory explains why GNNs fail on vertex-transitive graphs but succeeds on heterogeneous trace-index graphs. Using the CvS operator, we derive vanishing exponents βp = 0.122(4) uniformly across all primes - the first unconditional prediction of a fundamental operator-theoretic invariant proven by Connes.

Deep spectral analysis of 63K newforms reveals population-specific zero statistics: families with non-critical vanishing follow GUE spacing (gap ratio 6.1σ below GUE), while families with multiple critical zeros show suppressed small gaps. FunSearch discovers an optimal CM detection formula (F1 = 0.941) on 5 Sato-Tate islands, suggesting systematic ML-guided conjecture generation is possible.

This work demonstrates that strategic data scale (53K→200K forms), careful graph construction, and operator-theoretic insight - not deeper GNN architectures - are key to scientific discovery in number theory."""
        await page.evaluate(f"""(val) => {{
            const textarea = document.querySelector('textarea[name="metadata.description"]');
            if (textarea) {{
                Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(textarea, val);
                textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        }}""", abstract)

        # Keywords
        keywords = "modular forms, machine learning, graph neural networks, L-functions, Hecke traces, Sato-Tate, Connes colored vanishing spectrum"
        await page.evaluate(f"""(val) => {{
            const input = document.querySelector('input[name="metadata.keywords"]');
            if (input) {{
                Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, val);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        }}""", keywords)

        # Upload type
        print("Setting upload type...")
        await page.click("select[name='metadata.resource_type']")
        await page.select_option("publication")

        # Publication type
        await page.wait_for_timeout(1000)
        await page.click("select[name='metadata.publication_type']")
        await page.select_option("preprint")

        # Authors (single author for now)
        print("Adding authors...")
        # First author (Weiss, Tobias)
        await page.click("button:has-text('Add author')")
        await page.click("button:has-text('Submit')")  # Use personal

        # Fill author name if needed
        author_name_input = await page.query_selector("input[name*='name']")
        if author_name_input:
            await page.evaluate(f"""(val) => {{
                const input = document.querySelector('input[name*="name"]');
                if (input) {{
                    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, val);
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}""", "Weiss, Tobias")

            # Affiliation
            affiliation_input = await page.query_selector("input[name*='affiliation']")
            if affiliation_input:
                await page.evaluate(f"""(val) => {{
                    const input = document.querySelector('input[name*="affiliation"]');
                    if (input) {{
                        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, val);
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}""", "Independent Researcher")

        print("Metadata filled. Please review in the browser...")

        # Click publish button
        print("Clicking publish...")
        try:
            await page.click("button:has-text('Publish')")
            print("Publish clicked! Check browser for result.")
        except Exception as e:
            print(f"Publish click failed: {e}")
            print("Please click Publish manually in the browser.")

        # Wait a bit to see the result
        await page.wait_for_timeout(10000)

        print("Done. You can close the browser now.")

        # Don't close browser automatically - let user review


if __name__ == "__main__":
    asyncio.run(publish_to_zenodo())