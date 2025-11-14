"""
Demo script showing practical LLM usage for bid generation tasks
"""
import sys
import os
import json
# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.llm_config import generate_completion, get_llm_config
def demo_bid_generation():
    """Demo bid generation task"""
    print("=" * 60)
    print("DEMO: Bid Generation")
    print("=" * 60)
    sample_rfp = """
    RFP: Bottled Water Delivery Services
    Agency: City of Springfield Parks Department
    Contract Duration: 12 months
    Requirements:
    - Deliver 200 cases of 24-bottle spring water monthly
    - Delivery to 5 park locations
    - Must meet FDA standards
    - Local business preference (10% price advantage)
    - Delivery within 48 hours of order
    """
    prompt = f"""
    Based on the following RFP, generate a brief executive summary for our bid response:
    {sample_rfp}
    Include:
    1. Our value proposition
    2. Key capabilities
    3. Competitive advantages
    """
    system_message = """
    You are an expert bid writer for a water delivery company. 
    Your company has 15 years of experience, excellent delivery track record, 
    and specializes in municipal contracts. Focus on reliability, compliance, and local presence.
    """
    print("Generating bid content...")
    response = generate_completion(
        prompt=prompt,
        task_type="bid_generation",
        system_message=system_message
    )
    print(f"Status: {response['status']}")
    if response['status'] == 'success':
        print(f"Generated Content:\n{response['content']}")
        print(f"Model Used: {response.get('model', 'N/A')}")
        print(f"Token Usage: {response.get('usage', 'N/A')}")
    else:
        print(f"Error: {response.get('error', 'Unknown error')}")
def demo_requirement_extraction():
    """Demo requirement extraction task"""
    print("\n" + "=" * 60)
    print("DEMO: Requirement Extraction")
    print("=" * 60)
    rfp_text = """
    The contractor shall provide the following:
    1. Minimum of 500 cases of spring water per month
    2. All water must meet FDA and state health department standards
    3. Delivery within 48 hours of order placement
    4. Contractor must carry $2M liability insurance
    5. Monthly reporting of deliveries and quality metrics
    6. 24/7 emergency contact availability
    7. Vehicles must be properly refrigerated
    """
    prompt = f"""
    Extract all requirements from this RFP text and format as a structured list:
    {rfp_text}
    For each requirement, identify:
    - Requirement ID
    - Requirement text
    - Category (delivery, quality, legal, reporting, etc.)
    - Mandatory/Optional status
    """
    system_message = """
    You are a requirements analysis expert. Extract requirements precisely and categorize them systematically.
    Be thorough and identify implicit requirements as well as explicit ones.
    """
    print("Extracting requirements...")
    response = generate_completion(
        prompt=prompt,
        task_type="requirement_extraction",
        system_message=system_message
    )
    print(f"Status: {response['status']}")
    if response['status'] == 'success':
        print(f"Extracted Requirements:\n{response['content']}")
    else:
        print(f"Error: {response.get('error', 'Unknown error')}")
def demo_pricing_analysis():
    """Demo pricing analysis task"""
    print("\n" + "=" * 60)
    print("DEMO: Pricing Analysis")
    print("=" * 60)
    cost_data = {
        "base_cost_per_case": 2.50,
        "delivery_cost_per_location": 25.00,
        "insurance_monthly": 200.00,
        "reporting_cost_monthly": 100.00,
        "target_margin_percent": 40
    }
    contract_details = {
        "cases_per_month": 500,
        "delivery_locations": 5,
        "contract_months": 12
    }
    prompt = f"""
    Calculate competitive pricing for this contract with the following data:
    Cost Structure: {json.dumps(cost_data, indent=2)}
    Contract Details: {json.dumps(contract_details, indent=2)}
    Provide:
    1. Monthly cost breakdown
    2. Recommended bid price per month
    3. Total contract value
    4. Margin analysis
    5. Competitive positioning strategy
    """
    system_message = """
    You are a pricing specialist with expertise in government contracts and water delivery services.
    Consider market rates, margin requirements, and competitive factors in your analysis.
    """
    print("Analyzing pricing...")
    response = generate_completion(
        prompt=prompt,
        task_type="pricing_calculation",
        system_message=system_message
    )
    print(f"Status: {response['status']}")
    if response['status'] == 'success':
        print(f"Pricing Analysis:\n{response['content']}")
    else:
        print(f"Error: {response.get('error', 'Unknown error')}")
def demo_configuration_info():
    """Show current configuration info"""
    print("\n" + "=" * 60)
    print("CURRENT LLM CONFIGURATION")
    print("=" * 60)
    # Show configurations for different tasks
    tasks = ["bid_generation", "requirement_extraction", "pricing_calculation"]
    for task in tasks:
        config = get_llm_config(task)
        print(f"\nTask: {task}")
        print(f"  Provider: {config.provider.value}")
        print(f"  Model: {config.model_name}")
        print(f"  Temperature: {config.temperature}")
        print(f"  Max Tokens: {config.max_tokens}")
        print(f"  Has API Key: {bool(config.api_key)}")
if __name__ == "__main__":
    print("LLM Configuration Demo - Practical Usage Examples")
    print("=" * 70)
    # Show configuration
    demo_configuration_info()
    # Run practical demos
    demo_bid_generation()
    demo_requirement_extraction() 
    demo_pricing_analysis()
    print("\n" + "=" * 70)
    print("Demo completed! This shows how the LLM will be used in the bid generation system.")
    print("=" * 70)