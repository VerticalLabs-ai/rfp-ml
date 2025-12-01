#!/usr/bin/env python3
"""
Test script for enhanced proposal generation with Claude 4.5.

This script demonstrates:
1. Template-based generation (fast, basic)
2. Claude Sonnet 4.5 with thinking mode (recommended)
3. Claude Opus 4.5 with thinking mode (premium, most comprehensive)

Usage:
    python test_enhanced_proposal.py [--mode template|claude_enhanced|claude_premium]
"""
import argparse
import json
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config.paths import PathConfig


def test_claude_llm_config():
    """Test Claude LLM configuration module."""
    print("\n" + "=" * 60)
    print("Testing Claude LLM Configuration")
    print("=" * 60)

    try:
        from src.config.claude_llm_config import (
            ClaudeModel,
            ClaudeLLMConfig,
            create_claude_llm_manager,
        )

        # Check for API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("ANTHROPIC_API_KEY not set - Claude features will be unavailable")
            print("Set your API key in .env or environment to enable Claude generation")
            return False

        # Test configuration
        config = ClaudeLLMConfig()
        print(f"Model: {config.model.value}")
        print(f"Max Tokens: {config.max_tokens}")
        print(f"Thinking Enabled: {config.thinking.enabled}")
        print(f"Thinking Budget: {config.thinking.budget_tokens}")

        # Test manager creation
        manager = create_claude_llm_manager(
            model=ClaudeModel.SONNET_4_5,
            enable_thinking=True,
            thinking_budget=5000
        )

        validation = manager.validate_setup()
        print(f"\nSetup Valid: {validation['setup_valid']}")
        print(f"Connection Test: {validation.get('connection_test', 'N/A')}")

        if validation['errors']:
            print("Errors:")
            for error in validation['errors']:
                print(f"  - {error}")

        return validation['setup_valid']

    except ImportError as e:
        print(f"Import Error: {e}")
        print("Install anthropic package: pip install anthropic")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_enhanced_proposal_generator(mode: str = "claude_enhanced"):
    """Test enhanced proposal generator."""
    print("\n" + "=" * 60)
    print(f"Testing Enhanced Proposal Generator (Mode: {mode})")
    print("=" * 60)

    try:
        from src.bid_generation.enhanced_proposal_generator import (
            ProposalQuality,
            create_enhanced_proposal_generator,
        )

        # Create generator
        quality_map = {
            "standard": "standard",
            "claude_standard": "standard",
            "enhanced": "enhanced",
            "claude_enhanced": "enhanced",
            "premium": "premium",
            "claude_premium": "premium",
        }
        quality = quality_map.get(mode.lower(), "enhanced")

        generator = create_enhanced_proposal_generator(
            quality=quality,
            enable_thinking=True,
            thinking_budget=5000  # Lower for testing
        )

        print(f"Claude Available: {generator.is_available()}")

        if not generator.is_available():
            print("Claude not available - skipping enhanced generation test")
            return False

        # Test with sample RFP data
        test_rfp = {
            "title": "Enterprise IT Infrastructure Modernization Services",
            "agency": "Department of Defense",
            "description": """
            The Department of Defense requires comprehensive IT infrastructure
            modernization services including cloud migration, cybersecurity
            enhancement, and legacy system integration. The contractor shall
            provide planning, implementation, and ongoing support services for
            modernizing IT infrastructure across multiple DoD facilities.

            Key requirements include:
            - Cloud infrastructure design and implementation
            - Zero Trust security architecture implementation
            - Legacy system migration and integration
            - 24/7 operational support and monitoring
            - Compliance with NIST and DoD security standards
            - Training and knowledge transfer
            """,
            "naics_code": "541512",
            "award_amount": 2500000,
            "solicitation_number": "W91234-24-R-0001",
        }

        test_company = {
            "company_name": "IBYTE Enterprises, LLC",
            "certifications": [
                "Small Business",
                "Woman Owned Small Business (WOSB)",
                "ISO 27001 Certified",
                "CMMC Level 2 Certified"
            ],
            "core_competencies": [
                "IT Infrastructure & Cloud Services",
                "Cybersecurity",
                "Digital Transformation",
                "Government Contracting",
                "Project Management"
            ],
        }

        print("\nGenerating Executive Summary...")
        start_time = time.time()

        result = generator.generate_enhanced_section(
            section_type="executive_summary",
            rfp_data=test_rfp,
            company_profile=test_company,
        )

        generation_time = time.time() - start_time

        print(f"Status: {result.get('status')}")
        print(f"Word Count: {result.get('word_count', 0)}")
        print(f"Thinking Used: {result.get('thinking_enabled', False)}")
        print(f"Generation Time: {generation_time:.2f}s")

        if result.get("content"):
            print(f"\n--- Generated Content Preview ---")
            content_preview = result['content'][:1000]
            print(content_preview)
            if len(result['content']) > 1000:
                print(f"\n... [Content truncated, total {len(result['content'])} characters]")

        if result.get("thinking"):
            print(f"\n--- Thinking Process (Preview) ---")
            thinking_preview = result['thinking'][:500]
            print(thinking_preview)
            if len(result['thinking']) > 500:
                print(f"\n... [Thinking truncated]")

        return result.get("status") == "success"

    except ImportError as e:
        print(f"Import Error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_document_generator(mode: str = "template"):
    """Test document generator with different modes."""
    print("\n" + "=" * 60)
    print(f"Testing Document Generator (Mode: {mode})")
    print("=" * 60)

    try:
        import pandas as pd
        from src.bid_generation.document_generator import (
            BidDocumentGenerator,
            ProposalGenerationMode,
            ProposalGenerationOptions,
        )

        # Map mode string to enum
        mode_map = {
            "template": ProposalGenerationMode.TEMPLATE,
            "claude_standard": ProposalGenerationMode.CLAUDE_STANDARD,
            "claude_enhanced": ProposalGenerationMode.CLAUDE_ENHANCED,
            "claude_premium": ProposalGenerationMode.CLAUDE_PREMIUM,
        }
        gen_mode = mode_map.get(mode.lower(), ProposalGenerationMode.TEMPLATE)

        # Create options
        options = ProposalGenerationOptions(
            mode=gen_mode,
            enable_thinking=True,
            thinking_budget=5000
        )

        # Initialize generator
        generator = BidDocumentGenerator(proposal_options=options)

        print(f"Generation Mode: {options.mode.value}")
        print(f"Thinking Enabled: {options.enable_thinking}")
        print(f"Enhanced Generator Available: {generator.enhanced_generator is not None}")

        # Load test RFP data
        try:
            df = pd.read_parquet(str(PathConfig.PROCESSED_DATA_DIR / "rfp_master_dataset.parquet"))
            test_rfp = df[df['description'].notna()].iloc[0].to_dict()
            print(f"\nUsing real RFP: {test_rfp.get('title', 'Unknown')[:50]}...")
        except Exception:
            # Use sample data if parquet not available
            test_rfp = {
                "title": "Water Delivery Services for Federal Facilities",
                "agency": "General Services Administration",
                "description": "Procurement of bottled water delivery services.",
                "naics_code": "312112",
                "award_amount": 150000,
            }
            print("\nUsing sample RFP data")

        # Generate document
        print("\nGenerating bid document...")
        start_time = time.time()

        bid_document = generator.generate_bid_document(test_rfp)

        generation_time = time.time() - start_time

        # Display results
        print(f"\n--- Generation Results ---")
        print(f"Generation Time: {generation_time:.2f}s")
        print(f"Content Length: {bid_document['metadata']['document_stats']['content_length']:,} characters")
        print(f"Generation Mode Used: {bid_document['metadata']['generation_mode']}")
        print(f"Thinking Enabled: {bid_document['metadata']['thinking_enabled']}")
        print(f"Claude Enhanced: {bid_document['metadata']['claude_enhanced']}")

        # Export document
        output_path = generator.export_bid_document(bid_document, "markdown")
        print(f"\nDocument exported to: {output_path}")

        # Show executive summary preview
        exec_summary = bid_document['content']['sections']['executive_summary']
        print(f"\n--- Executive Summary Preview ---")
        print(exec_summary[:800] if len(exec_summary) > 800 else exec_summary)
        if len(exec_summary) > 800:
            print(f"\n... [Total: {len(exec_summary)} characters]")

        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def compare_generation_modes():
    """Compare template vs Claude enhanced generation."""
    print("\n" + "=" * 60)
    print("Comparing Generation Modes")
    print("=" * 60)

    # Check if Claude is available
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set - can only test template mode")
        test_document_generator("template")
        return

    # Test template mode
    print("\n[1/2] Testing Template Mode...")
    test_document_generator("template")

    # Test Claude enhanced mode
    print("\n[2/2] Testing Claude Enhanced Mode...")
    test_document_generator("claude_enhanced")


def main():
    parser = argparse.ArgumentParser(
        description="Test enhanced proposal generation with Claude 4.5"
    )
    parser.add_argument(
        "--mode",
        choices=["template", "claude_standard", "claude_enhanced", "claude_premium", "compare"],
        default="claude_enhanced",
        help="Generation mode to test"
    )
    parser.add_argument(
        "--test-config",
        action="store_true",
        help="Test Claude LLM configuration only"
    )
    parser.add_argument(
        "--test-enhanced",
        action="store_true",
        help="Test enhanced proposal generator only"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Enhanced Proposal Generation Test Suite")
    print("=" * 60)
    print(f"Mode: {args.mode}")

    results = {}

    # Test Claude configuration
    if args.test_config or not (args.test_enhanced):
        results["claude_config"] = test_claude_llm_config()

    # Test enhanced generator
    if args.test_enhanced or not (args.test_config):
        results["enhanced_generator"] = test_enhanced_proposal_generator(args.mode)

    # Test full document generation
    if not args.test_config and not args.test_enhanced:
        if args.mode == "compare":
            compare_generation_modes()
        else:
            results["document_generator"] = test_document_generator(args.mode)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {test_name}: {status}")

    # Exit code
    all_passed = all(results.values()) if results else True
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
