"""
NEXUS Cost Optimization Configuration
Central configuration for AI cost optimization services.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class DatabaseConfig:
    """Database configuration."""
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    name: str = os.getenv("POSTGRES_DB", "nexus_db")
    user: str = os.getenv("POSTGRES_USER", "nexus")
    password: str = os.getenv("POSTGRES_PASSWORD", "nexus_secure_b2fcd2b1e4056f11")
    
    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

@dataclass
class RedisConfig:
    """Redis configuration for caching."""
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    password: str = os.getenv("REDIS_PASSWORD", "redis_secure_46cbc763b7fcfd02")
    db: int = int(os.getenv("REDIS_DB", "0"))
    
    @property
    def connection_string(self) -> str:
        """Get Redis connection string."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

@dataclass
class AIProviderConfig:
    """Configuration for an AI provider."""
    name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    is_local: bool = False
    enabled: bool = True
    priority: int = 50  # Lower = higher priority
    monthly_budget: float = 0.0
    current_spend: float = 0.0
    
@dataclass
class AIModelConfig:
    """Configuration for an AI model."""
    provider_name: str
    model_id: str
    display_name: str
    context_window: int
    input_cost_per_mtok: float  # Cost per million tokens input
    output_cost_per_mtok: float  # Cost per million tokens output
    supports_tools: bool = False
    supports_vision: bool = False
    supports_caching: bool = True
    quality_score: float = 0.8  # 0-1
    speed_score: float = 0.8  # 0-1

@dataclass
class CostOptimizationConfig:
    """Cost optimization configuration."""
    # Cache settings
    semantic_cache_enabled: bool = True
    embedding_cache_enabled: bool = True
    cache_ttl_hours: int = 168  # 1 week
    
    # Model cascade settings
    cascade_enabled: bool = True
    min_complexity_for_premium: float = 0.7  # Use premium models for complexity > 0.7
    
    # Batch processing
    batch_processing_enabled: bool = True
    batch_size: int = 10
    batch_delay_seconds: int = 60
    
    # Cost alerts
    daily_budget: float = 1.0  # $1 per day
    monthly_budget: float = 30.0  # $30 per month
    alert_threshold_percent: float = 0.8  # Alert at 80% of budget
    
    # Semantic cache similarity threshold
    semantic_similarity_threshold: float = 0.85

@dataclass
class CostOptimizationServicesConfig:
    """Main configuration for cost optimization services."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    cost_optimization: CostOptimizationConfig = field(default_factory=CostOptimizationConfig)
    
    # AI Providers (loaded from environment)
    providers: Dict[str, AIProviderConfig] = field(default_factory=dict)
    
    # AI Models (configured in code for now)
    models: Dict[str, AIModelConfig] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize providers from environment."""
        self._load_providers_from_env()
        self._load_models_from_config()
    
    def _load_providers_from_env(self):
        """Load AI providers from environment variables."""
        # DeepSeek
        if os.getenv("DEEPSEEK_API_KEY"):
            self.providers["deepseek"] = AIProviderConfig(
                name="deepseek",
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                api_base="https://api.deepseek.com",
                is_local=False,
                enabled=True,
                priority=40,
                monthly_budget=10.0
            )
        
        # Groq
        if os.getenv("GROQ_API_KEY"):
            self.providers["groq"] = AIProviderConfig(
                name="groq",
                api_key=os.getenv("GROQ_API_KEY"),
                api_base="https://api.groq.com/openai/v1",
                is_local=False,
                enabled=True,
                priority=20,
                monthly_budget=5.0
            )
        
        # Anthropic (expensive, only for critical tasks)
        if os.getenv("ANTHROPIC_API_KEY"):
            self.providers["anthropic"] = AIProviderConfig(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                api_base="https://api.anthropic.com",
                is_local=False,
                enabled=True,
                priority=100,
                monthly_budget=15.0
            )
        
        # Ollama (local, free)
        self.providers["ollama"] = AIProviderConfig(
            name="ollama",
            api_base=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            is_local=True,
            enabled=True,
            priority=10,
            monthly_budget=0.0
        )
    
    def _load_models_from_config(self):
        """Load AI models configuration."""
        # Ollama models (free, local)
        self.models["llama3.2:3b"] = AIModelConfig(
            provider_name="ollama",
            model_id="llama3.2:3b",
            display_name="Llama 3.2 3B (Local)",
            context_window=8192,
            input_cost_per_mtok=0.0,
            output_cost_per_mtok=0.0,
            supports_tools=False,
            supports_vision=False,
            quality_score=0.6,
            speed_score=0.9
        )
        
        self.models["qwen2.5:7b"] = AIModelConfig(
            provider_name="ollama",
            model_id="qwen2.5:7b",
            display_name="Qwen 2.5 7B (Local)",
            context_window=32768,
            input_cost_per_mtok=0.0,
            output_cost_per_mtok=0.0,
            supports_tools=False,
            supports_vision=False,
            quality_score=0.7,
            speed_score=0.8
        )
        
        # DeepSeek models (cheap cloud)
        self.models["deepseek-chat"] = AIModelConfig(
            provider_name="deepseek",
            model_id="deepseek-chat",
            display_name="DeepSeek Chat",
            context_window=128000,
            input_cost_per_mtok=0.14,  # $0.14 per million tokens
            output_cost_per_mtok=0.28,  # $0.28 per million tokens
            supports_tools=True,
            supports_vision=False,
            quality_score=0.85,
            speed_score=0.8
        )
        
        # Groq models (fast, cheap)
        self.models["llama-3.1-8b-instant"] = AIModelConfig(
            provider_name="groq",
            model_id="llama-3.1-8b-instant",
            display_name="Llama 3.1 8B Instant (Groq)",
            context_window=8192,
            input_cost_per_mtok=0.10,  # $0.10 per million tokens
            output_cost_per_mtok=0.10,  # $0.10 per million tokens
            supports_tools=False,
            supports_vision=False,
            quality_score=0.75,
            speed_score=0.95
        )
        
        # Anthropic models (expensive, high quality)
        self.models["claude-3-haiku"] = AIModelConfig(
            provider_name="anthropic",
            model_id="claude-3-haiku",
            display_name="Claude 3 Haiku",
            context_window=200000,
            input_cost_per_mtok=0.25,  # $0.25 per million tokens
            output_cost_per_mtok=1.25,  # $1.25 per million tokens
            supports_tools=True,
            supports_vision=True,
            quality_score=0.9,
            speed_score=0.7
        )
        
        self.models["claude-3-opus"] = AIModelConfig(
            provider_name="anthropic",
            model_id="claude-3-opus",
            display_name="Claude 3 Opus",
            context_window=200000,
            input_cost_per_mtok=15.00,  # $15 per million tokens
            output_cost_per_mtok=75.00,  # $75 per million tokens
            supports_tools=True,
            supports_vision=True,
            quality_score=0.98,
            speed_score=0.5
        )
    
    def get_enabled_providers(self) -> Dict[str, AIProviderConfig]:
        """Get enabled providers sorted by priority."""
        enabled = {name: provider for name, provider in self.providers.items() 
                  if provider.enabled}
        return dict(sorted(enabled.items(), key=lambda x: x[1].priority))
    
    def get_available_models(self, provider_name: Optional[str] = None) -> Dict[str, AIModelConfig]:
        """Get available models, optionally filtered by provider."""
        if provider_name:
            return {name: model for name, model in self.models.items() 
                   if model.provider_name == provider_name and 
                   self.providers.get(model.provider_name, AIProviderConfig(name="")).enabled}
        return {name: model for name, model in self.models.items() 
               if self.providers.get(model.provider_name, AIProviderConfig(name="")).enabled}
    
    def get_model_cascade(self, task_type: str = "general") -> list:
        """Get model cascade for a given task type."""
        # Default cascade: local -> cheap cloud -> premium
        if task_type == "general":
            return [
                "llama3.2:3b",           # Free local
                "qwen2.5:7b",            # Free local (better)
                "llama-3.1-8b-instant",  # Cheap fast cloud
                "deepseek-chat",         # Good quality, reasonable cost
                "claude-3-haiku",        # High quality, moderate cost
                "claude-3-opus"          # Best quality, expensive
            ]
        elif task_type == "simple":
            return [
                "llama3.2:3b",
                "qwen2.5:7b",
                "llama-3.1-8b-instant"
            ]
        elif task_type == "complex":
            return [
                "deepseek-chat",
                "claude-3-haiku",
                "claude-3-opus"
            ]
        else:
            return self.get_model_cascade("general")

# Global configuration instance
config = CostOptimizationServicesConfig()

if __name__ == "__main__":
    # Test the configuration
    print("Loaded configuration:")
    print(f"Database: {config.database.connection_string}")
    print(f"Redis: {config.redis.connection_string}")
    print(f"Enabled providers: {list(config.get_enabled_providers().keys())}")
    print(f"Available models: {list(config.get_available_models().keys())}")
    print(f"General cascade: {config.get_model_cascade('general')}")
