"""
Demonstration of LLM infrastructure usage for bid generation tasks
"""
import sys

sys.path.append('/app/government_rfp_bid_1927/src')
import time

from config.llm_config import get_default_llm_manager


def demo_bid_generation_tasks():
    """Demonstrate LLM usage for different bid generation tasks"""
    print("=== LLM Bid Generation Demo ===\n")
    # Initialize manager
    manager = get_default_llm_manager()
    if not manager.is_available:
        print("❌ LLM not available. Please check configuration.")
        return
    print(f"Using: {manager.config.model_name} via {manager.config.provider}")
    print("-" * 50)
    # Demo 1: Requirement Extraction
    print("\n1. REQUIREMENT EXTRACTION DEMO")
    print("Task: Extract requirements from RFP text")
    sample_rfp_text = """
    The City of Springfield requires a contractor to provide bottled water delivery services 
    for all city facilities. Requirements include:
    - Deliver 500 cases of 16.9 oz bottled water weekly
    - Service period: 12 months with option for 2-year extension
    - Delivery schedule: Every Tuesday between 8 AM - 12 PM
    - All water must meet FDA standards
    - Contractor must have $1M liability insurance
    - Bid submission deadline: March 15, 2024
    """
    extraction_prompt = f"""
    Extract the key requirements from this RFP text and format them as a JSON list:
    {sample_rfp_text}
    Return only the JSON array with requirements, no additional text.
    """
    try:
        start_time = time.time()
        result = manager.generate_text(extraction_prompt, task_type="extraction", max_tokens=500)
        end_time = time.time()
        print(f"✅ Extraction completed in {end_time - start_time:.2f} seconds")
        print("Extracted requirements:")
        print(result["text"])
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
    # Demo 2: Bid Content Generation
    print("\n" + "="*50)
    print("2. BID CONTENT GENERATION DEMO")
    print("Task: Generate executive summary for water delivery bid")
    bid_prompt = """
    Write a professional executive summary for a bottled water delivery service bid. 
    Include our company's value proposition, experience, and commitment to quality.
    Keep it under 200 words and professional tone.
    Company: AquaFresh Delivery Services
    Experience: 15 years in beverage distribution
    Key strengths: Reliable delivery, competitive pricing, excellent customer service
    """
    try:
        start_time = time.time()
        result = manager.generate_text(bid_prompt, task_type="bid_generation", max_tokens=300)
        end_time = time.time()
        print(f"✅ Generation completed in {end_time - start_time:.2f} seconds")
        print("Generated executive summary:")
        print("-" * 30)
        print(result["text"])
        print("-" * 30)
    except Exception as e:
        print(f"❌ Generation failed: {e}")
    # Demo 3: Pricing Justification
    print("\n" + "="*50)
    print("3. PRICING JUSTIFICATION DEMO")
    print("Task: Generate pricing justification with margin analysis")
    pricing_prompt = """
    Generate a pricing justification for a weekly bottled water delivery service:
    Service Details:
    - 500 cases per week
    - 52 weeks per year
    - Cost per case: $3.50
    - Target margin: 40%
    - Market rate range: $4.50-$6.00 per case
    Provide calculated bid price and brief justification focusing on value and competitiveness.
    """
    try:
        start_time = time.time()
        result = manager.generate_text(pricing_prompt, task_type="pricing", max_tokens=400)
        end_time = time.time()
        print(f"✅ Pricing completed in {end_time - start_time:.2f} seconds")
        print("Generated pricing justification:")
        print("-" * 30)
        print(result["text"])
        print("-" * 30)
    except Exception as e:
        print(f"❌ Pricing failed: {e}")
    # Demo 4: Performance Summary
    print("\n" + "="*50)
    print("4. PERFORMANCE SUMMARY")
    model_info = manager.get_model_info()
    print(f"Provider: {model_info['provider']}")
    print(f"Model: {model_info['model_name']}")
    print(f"Available: {model_info['is_available']}")
    print("Temperature settings:")
    for task, temp in model_info['task_temperatures'].items():
        print(f"  - {task}: {temp}")
    print("\n🎉 LLM infrastructure demo complete!")
if __name__ == "__main__":
    demo_bid_generation_tasks()
