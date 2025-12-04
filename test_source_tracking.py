#!/usr/bin/env python3
"""
Test script to verify source tracking in requirement extraction.
"""
import sys
from src.compliance.compliance_matrix import ComplianceMatrixGenerator

def test_source_tracking():
    """Test that source tracking fields are properly extracted."""
    print("Testing Source Tracking Enhancement")
    print("=" * 60)

    # Create sample RFP text with document markers (simulating how the API formats it)
    sample_text = """
[RFP Description]
The contractor must provide monthly status reports.
All deliverables shall be submitted on time.

[Q&A]
Q: What format is required?
A: PDF format is required for all submissions.

=== Document: SOW.pdf ===
SECTION 1: TECHNICAL REQUIREMENTS

[Page 1]
The vendor shall implement security measures including encryption.
The contractor must provide 24/7 support services.

SECTION 2: PERFORMANCE METRICS
[Page 2]
The system must achieve 99.9% uptime.
Response time shall not exceed 2 seconds.

=== Document: Attachment_A.docx ===
ADMINISTRATIVE REQUIREMENTS

[Page 1]
All personnel must have security clearances.
The contractor shall maintain detailed logs.
"""

    # Test with ComplianceMatrixGenerator
    generator = ComplianceMatrixGenerator()

    # Test LLM-based extraction
    print("\n1. Testing LLM-based extraction:")
    print("-" * 60)
    llm_requirements = generator.extract_requirements_llm(sample_text)

    if not llm_requirements:
        print("WARNING: No requirements extracted by LLM method")
    else:
        print(f"Extracted {len(llm_requirements)} requirements")
        for i, req in enumerate(llm_requirements[:5], 1):  # Show first 5
            print(f"\nRequirement {i}:")
            print(f"  Text: {req['text'][:80]}...")
            print(f"  Source Document: {req.get('source_document', 'N/A')}")
            print(f"  Source Section: {req.get('source_section', 'N/A')}")
            print(f"  Source Page: {req.get('source_page', 'N/A')}")

    # Test rule-based extraction
    print("\n\n2. Testing Rule-based extraction:")
    print("-" * 60)
    rule_requirements = generator.extract_requirements_rule_based(sample_text)

    if not rule_requirements:
        print("WARNING: No requirements extracted by rule-based method")
    else:
        print(f"Extracted {len(rule_requirements)} requirements")
        for i, req in enumerate(rule_requirements[:5], 1):  # Show first 5
            print(f"\nRequirement {i}:")
            print(f"  Text: {req['text'][:80]}...")
            print(f"  Source Document: {req.get('source_document', 'N/A')}")
            print(f"  Source Section: {req.get('source_section', 'N/A')}")
            print(f"  Source Page: {req.get('source_page', 'N/A')}")

    # Verify source tracking is working
    print("\n\n3. Verification:")
    print("-" * 60)
    all_reqs = llm_requirements + rule_requirements

    has_source_doc = sum(1 for r in all_reqs if r.get('source_document'))
    has_source_section = sum(1 for r in all_reqs if r.get('source_section'))
    has_source_page = sum(1 for r in all_reqs if r.get('source_page'))

    print(f"Total requirements: {len(all_reqs)}")
    print(f"With source_document: {has_source_doc} ({has_source_doc/len(all_reqs)*100:.1f}%)")
    print(f"With source_section: {has_source_section} ({has_source_section/len(all_reqs)*100:.1f}%)")
    print(f"With source_page: {has_source_page} ({has_source_page/len(all_reqs)*100:.1f}%)")

    # Check for specific documents
    sow_reqs = [r for r in all_reqs if 'SOW.pdf' in str(r.get('source_document', ''))]
    attach_reqs = [r for r in all_reqs if 'Attachment_A.docx' in str(r.get('source_document', ''))]
    rfp_reqs = [r for r in all_reqs if 'RFP Description' in str(r.get('source_document', ''))]

    print(f"\nRequirements by document:")
    print(f"  RFP Description: {len(rfp_reqs)}")
    print(f"  SOW.pdf: {len(sow_reqs)}")
    print(f"  Attachment_A.docx: {len(attach_reqs)}")

    # Success criteria
    success = (
        len(all_reqs) > 0 and
        has_source_doc > 0 and
        (len(sow_reqs) > 0 or len(attach_reqs) > 0)
    )

    print("\n" + "=" * 60)
    if success:
        print("✓ SUCCESS: Source tracking is working!")
        return True
    else:
        print("✗ FAILURE: Source tracking not working as expected")
        return False

if __name__ == "__main__":
    success = test_source_tracking()
    sys.exit(0 if success else 1)
