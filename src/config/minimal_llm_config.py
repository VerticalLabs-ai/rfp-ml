"""
Minimal LLM Configuration Module for testing and basic functionality
"""
import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
class LLMBackend(Enum):
    """Supported LLM backends"""
    OPENAI_GPT4 = "openai_gpt4"
    OPENAI_GPT35 = "openai_gpt35"
    MOCK_LOCAL = "mock_local"
@dataclass
class LLMParameters:
    """LLM generation parameters"""
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 30
@dataclass
class MinimalLLMConfig:
    """Minimal LLM configuration"""
    primary_backend: LLMBackend = LLMBackend.OPENAI_GPT4
    fallback_backend: LLMBackend = LLMBackend.MOCK_LOCAL
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model_gpt4: str = "gpt-5.1"
    openai_model_gpt35: str = "gpt-3.5-turbo"
    # Generation parameters
    bid_generation_params: LLMParameters = None
    structured_extraction_params: LLMParameters = None
    pricing_params: LLMParameters = None
    def __post_init__(self):
        if not self.openai_api_key:
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if self.bid_generation_params is None:
            self.bid_generation_params = LLMParameters(temperature=0.7, max_tokens=2000)
        if self.structured_extraction_params is None:
            self.structured_extraction_params = LLMParameters(temperature=0.3, max_tokens=1000)
        if self.pricing_params is None:
            self.pricing_params = LLMParameters(temperature=0.5, max_tokens=800)
class MinimalLLMManager:
    """Minimal LLM management class"""
    def __init__(self, config: Optional[MinimalLLMConfig] = None):
        self.config = config or MinimalLLMConfig()
        self.logger = logging.getLogger(__name__)
        self.openai_client = None
        self.current_backend = None
        self._initialize_backends()
    def _initialize_backends(self):
        """Initialize available backends"""
        self.logger.info("Initializing minimal LLM backends...")
        if self._initialize_openai():
            self.current_backend = self.config.primary_backend
            self.logger.info(f"Primary backend {self.config.primary_backend.value} initialized")
        else:
            self.current_backend = self.config.fallback_backend
            self.logger.warning(f"Using fallback backend {self.config.fallback_backend.value}")
    def _initialize_openai(self) -> bool:
        """Initialize OpenAI client"""
        if not OPENAI_AVAILABLE:
            self.logger.warning("OpenAI package not available")
            return False
        if not self.config.openai_api_key:
            self.logger.warning("OpenAI API key not found")
            return False
        try:
            self.openai_client = openai.OpenAI(
                api_key=self.config.openai_api_key,
                timeout=self.config.bid_generation_params.timeout
            )
            # Test with a simple call
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model_gpt35,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            self.logger.info("OpenAI connection successful")
            return True
        except Exception as e:
            self.logger.error(f"OpenAI initialization failed: {str(e)}")
            return False
    def generate_text(
        self, 
        prompt: str, 
        use_case: str = "bid_generation",
        backend: Optional[LLMBackend] = None
    ) -> Dict[str, Any]:
        """Generate text using available backend"""
        # Select parameters
        if use_case == "structured_extraction":
            params = self.config.structured_extraction_params
        elif use_case == "pricing":
            params = self.config.pricing_params
        else:
            params = self.config.bid_generation_params
        selected_backend = backend or self.current_backend
        if selected_backend in [LLMBackend.OPENAI_GPT4, LLMBackend.OPENAI_GPT35] and self.openai_client:
            return self._generate_openai(prompt, params, selected_backend)
        else:
            return self._generate_mock(prompt, params, use_case)
    def _generate_openai(self, prompt: str, params: LLMParameters, backend: LLMBackend) -> Dict[str, Any]:
        """Generate using OpenAI"""
        model_name = (
            self.config.openai_model_gpt4 
            if backend == LLMBackend.OPENAI_GPT4 
            else self.config.openai_model_gpt35
        )
        response = self.openai_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=params.max_tokens,
            temperature=params.temperature
        )
        return {
            "text": response.choices[0].message.content,
            "backend": backend.value,
            "model": model_name,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "finish_reason": response.choices[0].finish_reason
        }
    def _generate_mock(self, prompt: str, params: LLMParameters, use_case: str) -> Dict[str, Any]:
        """Generate mock response for testing"""
        mock_responses = {
            "bid_generation": f"Mock bid response for: {prompt[:50]}... [Generated with temp={params.temperature}]",
            "structured_extraction": f"Mock structured data from: {prompt[:30]}... [Extracted requirements, deadlines, specifications]",
            "pricing": f"Mock pricing analysis for: {prompt[:30]}... [Competitive pricing with {params.temperature * 100:.0f}% confidence]"
        }
        response_text = mock_responses.get(use_case, f"Mock response for {use_case}: {prompt[:50]}...")
        return {
            "text": response_text,
            "backend": "mock_local",
            "model": "mock_model",
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(prompt.split()) + len(response_text.split())
            },
            "finish_reason": "mock_complete"
        }
    def test_connection(self) -> Dict[str, Any]:
        """Test connection"""
        try:
            result = self.generate_text(
                "Generate a brief professional greeting for a government bid proposal.",
                use_case="bid_generation"
            )
            return {
                "status": "success",
                "backend": result["backend"],
                "model": result["model"],
                "test_output": result["text"][:100] + "..." if len(result["text"]) > 100 else result["text"],
                "token_usage": result["usage"]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "backend": self.current_backend.value if self.current_backend else "none"
            }
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return {
            "current_backend": self.current_backend.value if self.current_backend else "none",
            "openai_available": self.openai_client is not None,
            "local_available": True,  # Mock is always available
            "device": "cpu",
            "openai_model_gpt4": self.config.openai_model_gpt4,
            "openai_model_gpt35": self.config.openai_model_gpt35,
            "local_model": "mock_model"
        }
def create_minimal_llm_manager(config_overrides: Optional[Dict[str, Any]] = None) -> MinimalLLMManager:
    """Create minimal LLM manager"""
    config = MinimalLLMConfig()
    if config_overrides:
        for key, value in config_overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
    return MinimalLLMManager(config)
if __name__ == "__main__":
    print("=== Minimal LLM Configuration Test ===")
    try:
        llm_manager = create_minimal_llm_manager()
        print("✓ LLM Manager created successfully")
        status = llm_manager.get_status()
        print(f"✓ Status: {status}")
        test_result = llm_manager.test_connection()
        print(f"✓ Connection test: {test_result}")
        # Test different use cases
        for use_case in ["bid_generation", "structured_extraction", "pricing"]:
            result = llm_manager.generate_text(f"Test prompt for {use_case}", use_case=use_case)
            print(f"✓ {use_case}: {result['text'][:50]}...")
        print("✅ Minimal LLM Configuration working!")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()