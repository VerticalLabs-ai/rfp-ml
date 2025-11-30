"""
Mock LLM implementation for testing and development without API keys
"""
import random
import time
from typing import Any


class MockLLMClient:
    """Mock LLM client that simulates OpenAI responses for testing"""
    def __init__(self, model_name: str = "mock-gpt-4"):
        self.model_name = model_name
    def chat_completions_create(self, model: str, messages: list, **kwargs) -> dict[str, Any]:
        """Mock the OpenAI chat completions API"""
        # Simulate API latency
        time.sleep(random.uniform(0.1, 0.5))
        prompt = messages[0]["content"] if messages else ""
        # Generate different responses based on prompt content
        if "executive summary" in prompt.lower():
            response_text = """
            AquaFresh Delivery Services brings 15 years of proven experience in beverage distribution
            to serve your bottled water delivery needs. Our commitment to reliable delivery,
            competitive pricing, and excellent customer service ensures your city facilities
            receive consistent, high-quality water supply. We guarantee FDA-compliant products,
            timely delivery schedules, and comprehensive insurance coverage for your peace of mind.
            """
        elif "extract" in prompt.lower() or "requirements" in prompt.lower():
            response_text = """
            [
                "Deliver 500 cases of 16.9 oz bottled water weekly",
                "Service period: 12 months with 2-year extension option",
                "Delivery schedule: Every Tuesday between 8 AM - 12 PM",
                "All water must meet FDA standards",
                "Contractor must have $1M liability insurance",
                "Bid submission deadline: March 15, 2024"
            ]
            """
        elif "pricing" in prompt.lower():
            response_text = """
            Based on the requirements for 500 cases per week at $3.50 cost per case,
            we propose a competitive bid price of $4.90 per case (40% margin).
            This totals $127,400 annually for 26,000 cases. Our pricing reflects
            industry-standard rates while ensuring quality service and reliable delivery.
            This competitive rate is 8% below market average of $5.30 per case.
            """
        elif "hello" in prompt.lower() or "connection" in prompt.lower():
            response_text = "Connection successful"
        else:
            response_text = "Mock response generated successfully for bid generation system testing."
        # Calculate token usage (approximate)
        prompt_tokens = len(prompt.split()) * 1.3  # Rough tokenization
        completion_tokens = len(response_text.split()) * 1.3
        return type('MockResponse', (), {
            'choices': [type('Choice', (), {
                'message': type('Message', (), {
                    'content': response_text.strip()
                })(),
                'finish_reason': 'stop'
            })()],
            'usage': type('Usage', (), {
                'prompt_tokens': int(prompt_tokens),
                'completion_tokens': int(completion_tokens),
                'total_tokens': int(prompt_tokens + completion_tokens)
            })()
        })()
def create_mock_openai_client(**kwargs):
    """Factory function to create mock OpenAI client"""
    return type('MockOpenAI', (), {
        'chat': type('Chat', (), {
            'completions': type('Completions', (), {
                'create': MockLLMClient().chat_completions_create
            })()
        })()
    })()
