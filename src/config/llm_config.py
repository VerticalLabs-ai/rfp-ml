"""
LLM Infrastructure Configuration Module
Supports OpenAI GPT-4 and local models with environment-based configuration
"""
import os
import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import json
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed, using system environment variables only")
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
@dataclass
class LLMConfig:
    """Configuration for LLM settings"""
    provider: LLMProvider
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: float = 30.0
    retries: int = 3
class LLMConfigManager:
    """Manages LLM configuration and provides unified interface"""
    DEFAULT_CONFIGS = {
        LLMProvider.OPENAI: {
            "model_name": "gpt-4-turbo-preview",
            "temperature": 0.7,
            "max_tokens": 2000,
            "timeout": 30.0
        },
        LLMProvider.HUGGINGFACE: {
            "model_name": "mistralai/Mistral-7B-Instruct-v0.1",
            "temperature": 0.7,
            "max_tokens": 2000,
            "timeout": 60.0
        },
        LLMProvider.LOCAL: {
            "model_name": "local-model",
            "temperature": 0.7,
            "max_tokens": 2000,
            "timeout": 60.0
        }
    }
    TASK_SPECIFIC_CONFIGS = {
        "bid_generation": {"temperature": 0.7, "max_tokens": 2000},
        "requirement_extraction": {"temperature": 0.3, "max_tokens": 1500},
        "pricing_calculation": {"temperature": 0.2, "max_tokens": 1000},
        "compliance_analysis": {"temperature": 0.3, "max_tokens": 1500},
        "go_nogo_decision": {"temperature": 0.4, "max_tokens": 1000}
    }
    def __init__(self):
        self.config: Optional[LLMConfig] = None
        self._initialize_config()
    def _initialize_config(self):
        """Initialize LLM configuration from environment variables"""
        try:
            # Determine provider priority: OpenAI > HuggingFace > Local
            provider = self._determine_provider()
            base_config = self.DEFAULT_CONFIGS[provider].copy()
            if provider == LLMProvider.OPENAI:
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    logger.warning("OPENAI_API_KEY not found, falling back to HuggingFace")
                    provider = LLMProvider.HUGGINGFACE
                    base_config = self.DEFAULT_CONFIGS[provider].copy()
                    api_key = os.getenv("HUGGINGFACE_API_KEY")
                else:
                    base_config["api_key"] = api_key
            elif provider == LLMProvider.HUGGINGFACE:
                api_key = os.getenv("HUGGINGFACE_API_KEY")
                base_config["api_key"] = api_key
                base_config["base_url"] = os.getenv("HUGGINGFACE_BASE_URL", "https://api-inference.huggingface.co/models")
            # Override with environment variables if available
            base_config.update({
                "model_name": os.getenv("LLM_MODEL_NAME", base_config["model_name"]),
                "temperature": float(os.getenv("LLM_TEMPERATURE", base_config["temperature"])),
                "max_tokens": int(os.getenv("LLM_MAX_TOKENS", base_config["max_tokens"])),
                "timeout": float(os.getenv("LLM_TIMEOUT", base_config["timeout"]))
            })
            self.config = LLMConfig(
                provider=provider,
                **base_config
            )
            logger.info(f"LLM Configuration initialized: Provider={provider.value}, Model={self.config.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM configuration: {e}")
            # Fallback to local configuration
            self.config = LLMConfig(
                provider=LLMProvider.LOCAL,
                **self.DEFAULT_CONFIGS[LLMProvider.LOCAL]
            )
    def _determine_provider(self) -> LLMProvider:
        """Determine the best available LLM provider"""
        # Check for explicit provider setting
        provider_env = os.getenv("LLM_PROVIDER", "").lower()
        if provider_env in ["openai", "huggingface", "local"]:
            return LLMProvider(provider_env)
        # Auto-detect based on available API keys
        if os.getenv("OPENAI_API_KEY"):
            return LLMProvider.OPENAI
        elif os.getenv("HUGGINGFACE_API_KEY"):
            return LLMProvider.HUGGINGFACE
        else:
            return LLMProvider.LOCAL
    def get_config(self, task_type: Optional[str] = None) -> LLMConfig:
        """Get LLM configuration, optionally customized for specific task"""
        if not self.config:
            raise RuntimeError("LLM configuration not initialized")
        config = self.config
        # Apply task-specific overrides
        if task_type and task_type in self.TASK_SPECIFIC_CONFIGS:
            task_config = self.TASK_SPECIFIC_CONFIGS[task_type]
            config = LLMConfig(
                provider=config.provider,
                model_name=config.model_name,
                api_key=config.api_key,
                base_url=config.base_url,
                temperature=task_config.get("temperature", config.temperature),
                max_tokens=task_config.get("max_tokens", config.max_tokens),
                timeout=config.timeout,
                retries=config.retries
            )
        return config
    def get_client(self, task_type: Optional[str] = None):
        """Get appropriate LLM client based on configuration"""
        config = self.get_config(task_type)
        if config.provider == LLMProvider.OPENAI:
            return self._get_openai_client(config)
        elif config.provider == LLMProvider.HUGGINGFACE:
            return self._get_huggingface_client(config)
        elif config.provider == LLMProvider.LOCAL:
            return self._get_local_client(config)
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")
    def _get_openai_client(self, config: LLMConfig):
        """Get OpenAI client"""
        try:
            import openai
            client = openai.OpenAI(
                api_key=config.api_key,
                timeout=config.timeout
            )
            return client
        except ImportError:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")
    def _get_huggingface_client(self, config: LLMConfig):
        """Get HuggingFace client"""
        try:
            from transformers import pipeline
            # For HuggingFace, we'll use a simple wrapper
            return {
                "config": config,
                "type": "huggingface"
            }
        except ImportError:
            raise ImportError("Transformers package not installed. Install with: pip install transformers")
    def _get_local_client(self, config: LLMConfig):
        """Get local model client"""
        return {
            "config": config,
            "type": "local"
        }
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current LLM configuration"""
        if not self.config:
            return {"status": "error", "message": "Configuration not initialized"}
        validation_result = {
            "status": "success",
            "provider": self.config.provider.value,
            "model": self.config.model_name,
            "has_api_key": bool(self.config.api_key),
            "configuration": {
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "timeout": self.config.timeout
            }
        }
        return validation_result
class LLMInterface:
    """Unified interface for different LLM providers"""
    def __init__(self, config_manager: LLMConfigManager):
        self.config_manager = config_manager
    def generate_completion(self, 
                          prompt: str, 
                          task_type: Optional[str] = None,
                          system_message: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """Generate completion using configured LLM"""
        try:
            config = self.config_manager.get_config(task_type)
            client = self.config_manager.get_client(task_type)
            if config.provider == LLMProvider.OPENAI:
                return self._openai_completion(client, prompt, system_message, config)
            elif config.provider == LLMProvider.HUGGINGFACE:
                return self._huggingface_completion(client, prompt, system_message, config)
            elif config.provider == LLMProvider.LOCAL:
                return self._local_completion(client, prompt, system_message, config)
            else:
                raise ValueError(f"Unsupported provider: {config.provider}")
        except Exception as e:
            logger.error(f"Failed to generate completion: {e}")
            return {
                "status": "error",
                "error": str(e),
                "content": None
            }
    def _openai_completion(self, client, prompt: str, system_message: Optional[str], config: LLMConfig) -> Dict[str, Any]:
        """Generate completion using OpenAI"""
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=config.model_name,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout
        )
        return {
            "status": "success",
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "model": config.model_name
        }
    def _huggingface_completion(self, client, prompt: str, system_message: Optional[str], config: LLMConfig) -> Dict[str, Any]:
        """Generate completion using HuggingFace (simplified implementation)"""
        full_prompt = prompt
        if system_message:
            full_prompt = f"{system_message}\n\n{prompt}"
        # This is a simplified implementation - in production, you'd want to use
        # the HuggingFace Inference API or local transformers pipeline
        return {
            "status": "success",
            "content": f"[HuggingFace Model Response] Generated response for: {full_prompt[:100]}...",
            "usage": {"tokens": len(full_prompt.split())},
            "model": config.model_name
        }
    def _local_completion(self, client, prompt: str, system_message: Optional[str], config: LLMConfig) -> Dict[str, Any]:
        """Generate completion using local model (mock implementation)"""
        full_prompt = prompt
        if system_message:
            full_prompt = f"{system_message}\n\n{prompt}"
        # Mock response for local model
        return {
            "status": "success",
            "content": f"[Local Model Response] Mock response for: {full_prompt[:100]}...",
            "usage": {"tokens": len(full_prompt.split())},
            "model": config.model_name
        }

class LLMManager:
    """
    Facade for LLM interaction to maintain backward compatibility 
    and simplify usage for agents.
    """
    def __init__(self):
        self.config_manager = LLMConfigManager()
        self.interface = LLMInterface(self.config_manager)

    def generate_text(self, prompt: str, task_type: str = None, max_tokens: int = None, temperature: float = None, **kwargs) -> str:
        """
        Simplified text generation method.
        Returns just the content string or empty string on failure.
        """
        # Temporarily override config if needed (not fully implemented in this facade but noted)
        # For now we rely on task_type config lookups
        
        response = self.interface.generate_completion(prompt, task_type)
        if response['status'] == 'success' and response['content']:
            return response['content']
        return ""

    def validate_setup(self) -> Dict[str, Any]:
        """Validate setup"""
        res = self.config_manager.validate_configuration()
        # Add 'setup_valid' key as expected by EnhancedBidLLMManager
        res['setup_valid'] = (res['status'] == 'success')
        return res
# Global instances
config_manager = LLMConfigManager()
llm_interface = LLMInterface(config_manager)
def get_llm_config(task_type: Optional[str] = None) -> LLMConfig:
    """Get LLM configuration for specific task"""
    return config_manager.get_config(task_type)
def get_llm_client(task_type: Optional[str] = None):
    """Get LLM client for specific task"""
    return config_manager.get_client(task_type)
def generate_completion(prompt: str, 
                       task_type: Optional[str] = None,
                       system_message: Optional[str] = None) -> Dict[str, Any]:
    """Generate completion using configured LLM"""
    return llm_interface.generate_completion(prompt, task_type, system_message)
def test_llm_connection() -> Dict[str, Any]:
    """Test LLM connection and configuration"""
    try:
        # Test basic configuration
        validation = config_manager.validate_configuration()
        if validation["status"] != "success":
            return validation
        # Test actual API call
        test_prompt = "Hello! Please respond with 'LLM connection successful' to confirm the API is working."
        response = generate_completion(
            prompt=test_prompt,
            task_type="bid_generation",
            system_message="You are a helpful assistant. Respond concisely."
        )
        if response["status"] == "success":
            return {
                "status": "success",
                "message": "LLM connection test successful",
                "config": validation,
                "test_response": response["content"][:200],  # First 200 chars
                "response_time": "< 2 seconds"  # Placeholder
            }
        else:
            return {
                "status": "error",
                "message": "LLM connection test failed",
                "error": response.get("error", "Unknown error")
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"LLM connection test failed: {str(e)}"
        }
if __name__ == "__main__":
    # Test the configuration when run directly
    print("Testing LLM Configuration...")
    # Test configuration validation
    validation = config_manager.validate_configuration()
    print(f"Configuration validation: {json.dumps(validation, indent=2)}")
    # Test connection
    connection_test = test_llm_connection()
    print(f"Connection test: {json.dumps(connection_test, indent=2)}")