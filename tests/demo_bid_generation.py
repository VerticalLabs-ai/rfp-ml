"""
Demonstration script showing LLM infrastructure generating actual bid content
"""
import sys

sys.path.append('/app/government_rfp_bid_1927')
from src.config.production_llm_config import BidGenerationLLMManager


def demo_bid_generation():
    """Demonstrate bid generation capabilities"""
    print("🚀 DEMO: AI-Powered Bid Generation")
    print("=" * 50)
    # Initialize bid generation manager
    manager = BidGenerationLLMManager()
    # Sample RFP scenario
    sample_rfp = """
    Request for Proposal: Bottled Water Delivery Services
    The Department of General Services seeks a qualified vendor to provide 
    bottled water delivery services to 15 government office locations for 
    a period of 24 months. Services must include:
    - Weekly delivery of 5-gallon water bottles
    - All water must meet FDA standards
    - Delivery tracking and inventory management
    - Emergency delivery capability within 24 hours
    - Vendor must carry $1M general liability insurance
    - Minimum 5 years experience in commercial water delivery
    Contract value estimated at $150,000 over 24 months.
    """
    print("\n📋 Sample RFP:")
    print(sample_rfp)
    # Extract requirements
    print("\n🔍 Extracting Requirements...")
    requirements = manager.extract_requirements(sample_rfp)
    print(f"   ✓ Extracted {len(requirements)} requirements:")
    for req_id, req_text in requirements.items():
        print(f"     • {req_id}: {req_text}")
    # Generate bid sections
    print("\n📝 Generating Bid Sections...")
    sections_to_generate = [
        ("executive_summary", "Executive Summary", 200),
        ("company_qualifications", "Company Qualifications", 250),
        ("technical_approach", "Technical Approach", 300)
    ]
    generated_bid = {}
    for section_id, section_name, max_words in sections_to_generate:
        print(f"\n   Generating {section_name}...")
        result = manager.generate_bid_section(
            section_id,
            sample_rfp,
            requirements,
            max_words=max_words
        )
        if result["status"] == "generated":
            generated_bid[section_id] = result
            print(f"   ✓ Generated {result['word_count']} words")
            print(f"   ✓ Quality score: {result['confidence_score']:.2f}")
            print(f"   ✓ Requirements addressed: {len(result['requirements_addressed'])}")
        else:
            print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
    # Display generated bid
    print("\n" + "=" * 60)
    print("📄 GENERATED BID DOCUMENT")
    print("=" * 60)
    for section_id, section_name, _ in sections_to_generate:
        if section_id in generated_bid:
            section_data = generated_bid[section_id]
            print(f"\n{section_name.upper()}")
            print("-" * len(section_name))
            print(section_data['content'])
            print(f"\n[Word Count: {section_data['word_count']}, Quality Score: {section_data['confidence_score']:.2f}]")
    # Summary
    print("\n" + "=" * 60)
    print("📊 GENERATION SUMMARY")
    print("=" * 60)
    total_sections = len(sections_to_generate)
    successful_sections = len(generated_bid)
    total_words = sum(section['word_count'] for section in generated_bid.values())
    avg_quality = sum(section['confidence_score'] for section in generated_bid.values()) / successful_sections if successful_sections > 0 else 0
    print(f"Sections generated: {successful_sections}/{total_sections}")
    print(f"Total words: {total_words}")
    print(f"Average quality score: {avg_quality:.2f}")
    print(f"Requirements extracted: {len(requirements)}")
    if successful_sections == total_sections:
        print("\n✅ Bid generation SUCCESSFUL - Ready for integration with RAG system!")
    else:
        print("\n⚠️  Partial success - Some sections failed to generate")
    return successful_sections == total_sections
if __name__ == "__main__":
    success = demo_bid_generation()
    sys.exit(0 if success else 1)
