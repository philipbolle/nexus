"""
NEXUS Model Router
Intelligent routing of AI requests to optimize cost, latency, and quality.
"""

import asyncio
import json
import hashlib
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from uuid import UUID
from .config import config
from .cache_service import cache_service
from .cost_tracker import cost_tracker

class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    CRITICAL = "critical"

@dataclass
class RoutingDecision:
    """Decision made by the model router."""
    selected_model: str
    provider_name: str
    reason: str
    estimated_cost_usd: float
    estimated_latency_ms: float
    confidence_score: float = 1.0
    fallback_models: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_model": self.selected_model,
            "provider_name": self.provider_name,
            "reason": self.reason,
            "estimated_cost_usd": self.estimated_cost_usd,
            "estimated_latency_ms": self.estimated_latency_ms,
            "confidence_score": self.confidence_score,
            "fallback_models": self.fallback_models or []
        }

class ModelRouter:
    """
    Intelligent router that selects the best AI model for each request
    based on cost, latency, quality, and task requirements.
    """
    
    def __init__(self):
        self.config = config
        self.cache_service = cache_service
        self.cost_tracker = cost_tracker
        
    async def initialize(self):
        """Initialize the model router."""
        await self.cache_service.initialize()
        await self.cost_tracker.initialize()
    
    async def close(self):
        """Close the model router."""
        pass  # Services are closed separately
    
    # ===== Model Selection =====
    
    async def select_model(
        self,
        task_description: str,
        task_type: str = "general",
        required_capabilities: Optional[List[str]] = None,
        budget_constraints: Optional[Dict[str, float]] = None,
        latency_constraints: Optional[Dict[str, float]] = None,
        quality_constraints: Optional[Dict[str, float]] = None
    ) -> RoutingDecision:
        """
        Select the best model for a given task.
        
        Args:
            task_description: Description of the task
            task_type: Type of task (e.g., "chat", "summarization", "code")
            required_capabilities: Required capabilities (e.g., ["tools", "vision"])
            budget_constraints: Budget constraints (e.g., {"max_cost_usd": 0.01})
            latency_constraints: Latency constraints (e.g., {"max_ms": 1000})
            quality_constraints: Quality constraints (e.g., {"min_score": 0.8})
        
        Returns:
            RoutingDecision with selected model and reasoning
        """
        # Analyze task complexity
        complexity = self._analyze_task_complexity(task_description, task_type)
        
        # Get candidate models
        candidates = self._get_candidate_models(
            complexity=complexity,
            required_capabilities=required_capabilities,
            budget_constraints=budget_constraints,
            latency_constraints=latency_constraints,
            quality_constraints=quality_constraints
        )
        
        if not candidates:
            # Fallback to default cascade
            return await self._get_fallback_decision(complexity)
        
        # Score and rank candidates
        ranked = self._rank_candidates(candidates, complexity)
        
        # Select best model
        best_model = ranked[0]
        
        # Prepare fallback models
        fallback_models = [model["model_id"] for model in ranked[1:3] if model["model_id"]]
        
        # Create routing decision
        decision = RoutingDecision(
            selected_model=best_model["model_id"],
            provider_name=best_model["provider_name"],
            reason=f"Selected based on {best_model['selection_reason']}",
            estimated_cost_usd=best_model["estimated_cost"],
            estimated_latency_ms=best_model["estimated_latency"],
            confidence_score=best_model["confidence_score"],
            fallback_models=fallback_models
        )
        
        return decision
    
    def _analyze_task_complexity(self, task_description: str, task_type: str) -> TaskComplexity:
        """Analyze task complexity."""
        # Simple heuristic based on task type and description length
        if task_type in ["simple_query", "classification", "translation"]:
            return TaskComplexity.SIMPLE
        elif task_type in ["summarization", "paraphrasing", "sentiment"]:
            return TaskComplexity.MEDIUM
        elif task_type in ["code_generation", "analysis", "reasoning"]:
            return TaskComplexity.COMPLEX
        elif task_type in ["critical", "safety", "legal"]:
            return TaskComplexity.CRITICAL
        
        # Fallback based on description length
        word_count = len(task_description.split())
        if word_count < 20:
            return TaskComplexity.SIMPLE
        elif word_count < 100:
            return TaskComplexity.MEDIUM
        elif word_count < 500:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.CRITICAL
    
    def _get_candidate_models(
        self,
        complexity: TaskComplexity,
        required_capabilities: Optional[List[str]] = None,
        budget_constraints: Optional[Dict[str, float]] = None,
        latency_constraints: Optional[Dict[str, float]] = None,
        quality_constraints: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """Get candidate models that meet the constraints."""
        candidates = []
        available_models = self.config.get_available_models()
        
        for model_id, model_config in available_models.items():
            # Check if model is enabled
            provider = self.config.providers.get(model_config.provider_name)
            if not provider or not provider.enabled:
                continue
            
            # Check capabilities
            if required_capabilities:
                if "tools" in required_capabilities and not model_config.supports_tools:
                    continue
                if "vision" in required_capabilities and not model_config.supports_vision:
                    continue
            
            # Check budget constraints
            if budget_constraints:
                max_cost = budget_constraints.get("max_cost_usd")
                if max_cost is not None and model_config.input_cost_per_mtok > max_cost * 1000:
                    continue
            
            # Check quality constraints
            if quality_constraints:
                min_score = quality_constraints.get("min_score", 0)
                if model_config.quality_score < min_score:
                    continue
            
            # Check if model is appropriate for complexity
            if not self._is_model_appropriate_for_complexity(model_config, complexity):
                continue
            
            # Estimate cost and latency
            estimated_cost = self._estimate_cost(model_config, complexity)
            estimated_latency = self._estimate_latency(model_config, complexity)
            
            # Check latency constraints
            if latency_constraints:
                max_latency = latency_constraints.get("max_ms")
                if max_latency is not None and estimated_latency > max_latency:
                    continue
            
            candidates.append({
                "model_id": model_id,
                "model_config": model_config,
                "provider_name": model_config.provider_name,
                "provider_config": provider,
                "estimated_cost": estimated_cost,
                "estimated_latency": estimated_latency,
                "quality_score": model_config.quality_score,
                "speed_score": model_config.speed_score
            })
        
        return candidates
    
    def _is_model_appropriate_for_complexity(self, model_config: Any, complexity: TaskComplexity) -> bool:
        """Check if model is appropriate for task complexity."""
        # Local models for simple tasks
        if model_config.provider_name == "ollama":
            return complexity in [TaskComplexity.SIMPLE, TaskComplexity.MEDIUM]
        
        # Cheap cloud models for medium tasks
        if model_config.provider_name in ["groq", "deepseek"]:
            return complexity in [TaskComplexity.SIMPLE, TaskComplexity.MEDIUM, TaskComplexity.COMPLEX]
        
        # Premium models for complex/critical tasks
        if model_config.provider_name == "anthropic":
            return complexity in [TaskComplexity.COMPLEX, TaskComplexity.CRITICAL]
        
        return True
    
    def _estimate_cost(self, model_config: Any, complexity: TaskComplexity) -> float:
        """Estimate cost for a task of given complexity."""
        # Base token estimates based on complexity
        if complexity == TaskComplexity.SIMPLE:
            input_tokens = 100
            output_tokens = 50
        elif complexity == TaskComplexity.MEDIUM:
            input_tokens = 500
            output_tokens = 200
        elif complexity == TaskComplexity.COMPLEX:
            input_tokens = 2000
            output_tokens = 500
        else:  # CRITICAL
            input_tokens = 5000
            output_tokens = 1000
        
        input_cost = (input_tokens * model_config.input_cost_per_mtok) / 1_000_000
        output_cost = (output_tokens * model_config.output_cost_per_mtok) / 1_000_000
        
        return input_cost + output_cost
    
    def _estimate_latency(self, model_config: Any, complexity: TaskComplexity) -> float:
        """Estimate latency for a task of given complexity."""
        # Base latency based on provider and model speed
        base_latency = 1000  # ms
        
        if model_config.provider_name == "ollama":
            base_latency = 2000  # Local models are slower
        elif model_config.provider_name == "groq":
            base_latency = 500  # Groq is very fast
        elif model_config.provider_name == "deepseek":
            base_latency = 1500
        elif model_config.provider_name == "anthropic":
            base_latency = 3000
        
        # Adjust for complexity
        complexity_multiplier = {
            TaskComplexity.SIMPLE: 0.5,
            TaskComplexity.MEDIUM: 1.0,
            TaskComplexity.COMPLEX: 2.0,
            TaskComplexity.CRITICAL: 3.0
        }
        
        # Adjust for model speed
        speed_multiplier = 2.0 - model_config.speed_score  # Higher speed = lower multiplier
        
        return base_latency * complexity_multiplier[complexity] * speed_multiplier
    
    def _rank_candidates(self, candidates: List[Dict[str, Any]], complexity: TaskComplexity) -> List[Dict[str, Any]]:
        """Rank candidate models based on multiple factors."""
        if not candidates:
            return []
        
        for candidate in candidates:
            # Calculate weighted score
            cost_score = self._calculate_cost_score(candidate["estimated_cost"], complexity)
            latency_score = self._calculate_latency_score(candidate["estimated_latency"], complexity)
            quality_score = candidate["quality_score"]
            
            # Weights based on complexity
            if complexity == TaskComplexity.SIMPLE:
                weights = {"cost": 0.5, "latency": 0.3, "quality": 0.2}
            elif complexity == TaskComplexity.MEDIUM:
                weights = {"cost": 0.4, "latency": 0.3, "quality": 0.3}
            elif complexity == TaskComplexity.COMPLEX:
                weights = {"cost": 0.3, "latency": 0.3, "quality": 0.4}
            else:  # CRITICAL
                weights = {"cost": 0.2, "latency": 0.3, "quality": 0.5}
            
            total_score = (
                cost_score * weights["cost"] +
                latency_score * weights["latency"] +
                quality_score * weights["quality"]
            )
            
            candidate["total_score"] = total_score
            candidate["selection_reason"] = self._get_selection_reason(
                cost_score, latency_score, quality_score, weights
            )
            candidate["confidence_score"] = total_score
        
        # Sort by total score (descending)
        return sorted(candidates, key=lambda x: x["total_score"], reverse=True)
    
    def _calculate_cost_score(self, estimated_cost: float, complexity: TaskComplexity) -> float:
        """Calculate cost score (lower cost = higher score)."""
        # Normalize cost on a logarithmic scale
        if estimated_cost == 0:
            return 1.0
        
        # Reference costs based on complexity
        ref_costs = {
            TaskComplexity.SIMPLE: 0.001,
            TaskComplexity.MEDIUM: 0.01,
            TaskComplexity.COMPLEX: 0.1,
            TaskComplexity.CRITICAL: 1.0
        }
        
        ref_cost = ref_costs[complexity]
        normalized = ref_cost / max(estimated_cost, 0.0001)
        
        # Cap at 1.0
        return min(normalized, 1.0)
    
    def _calculate_latency_score(self, estimated_latency: float, complexity: TaskComplexity) -> float:
        """Calculate latency score (lower latency = higher score)."""
        # Reference latencies based on complexity
        ref_latencies = {
            TaskComplexity.SIMPLE: 1000,
            TaskComplexity.MEDIUM: 3000,
            TaskComplexity.COMPLEX: 10000,
            TaskComplexity.CRITICAL: 30000
        }
        
        ref_latency = ref_latencies[complexity]
        normalized = ref_latency / max(estimated_latency, 100)
        
        # Cap at 1.0
        return min(normalized, 1.0)
    
    def _get_selection_reason(self, cost_score: float, latency_score: float, 
                             quality_score: float, weights: Dict[str, float]) -> str:
        """Get human-readable reason for selection."""
        if cost_score * weights["cost"] > 0.4:
            return "best cost efficiency"
        elif latency_score * weights["latency"] > 0.4:
            return "best latency performance"
        elif quality_score * weights["quality"] > 0.4:
            return "best quality output"
        else:
            return "balanced performance across cost, latency, and quality"
    
    async def _get_fallback_decision(self, complexity: TaskComplexity) -> RoutingDecision:
        """Get fallback decision when no candidates match constraints."""
        # Use model cascade from config
        if complexity == TaskComplexity.SIMPLE:
            cascade = self.config.get_model_cascade("simple")
        elif complexity == TaskComplexity.COMPLEX or complexity == TaskComplexity.CRITICAL:
            cascade = self.config.get_model_cascade("complex")
        else:
            cascade = self.config.get_model_cascade("general")
        
        # Find first available model in cascade
        selected_model = None
        for model_id in cascade:
            if model_id in self.config.models:
                model_config = self.config.models[model_id]
                provider = self.config.providers.get(model_config.provider_name)
                if provider and provider.enabled:
                    selected_model = model_id
                    break
        
        if not selected_model:
            # Ultimate fallback
            selected_model = "llama3.2:3b"
        
        model_config = self.config.models[selected_model]
        estimated_cost = self._estimate_cost(model_config, complexity)
        estimated_latency = self._estimate_latency(model_config, complexity)
        
        return RoutingDecision(
            selected_model=selected_model,
            provider_name=model_config.provider_name,
            reason="Fallback to cascade (no suitable models matched constraints)",
            estimated_cost_usd=estimated_cost,
            estimated_latency_ms=estimated_latency,
            confidence_score=0.5,
            fallback_models=[]
        )
    
    # ===== Request Processing =====
    
    async def process_request(
        self,
        messages: List[Dict[str, str]],
        task_type: str = "general",
        agent_id: Optional[UUID] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a request with intelligent model selection and caching.
        
        Args:
            messages: List of message dicts with "role" and "content"
            task_type: Type of task
            **kwargs: Additional parameters for model selection
        
        Returns:
            Response dict with content, model used, and metadata
        """
        start_time = time.time()
        
        # Check cache first
        query_text = self._messages_to_text(messages)
        cached_response = await self.cache_service.get_semantic_cache(query_text, agent_id)
        
        if cached_response:
            # Cache hit
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Track cache hit
            await self.cost_tracker.track_api_call(
                provider_name=cached_response.get("provider_name", "unknown"),
                model_id=cached_response.get("model_used", "unknown"),
                input_tokens=len(query_text) // 4,  # Rough estimate
                output_tokens=len(cached_response.get("response_text", "")) // 4,
                cached_tokens=cached_response.get("tokens_saved", 0),
                cache_hit=True,
                latency_ms=latency_ms,
                query_hash=cached_response.get("query_hash"),
                agent_id=agent_id
            )
            
            return {
                "content": cached_response["response_text"],
                "model_used": cached_response["model_used"],
                "cached": True,
                "cache_confidence": cached_response.get("confidence_score", 0.9),
                "tokens_saved": cached_response.get("tokens_saved", 0),
                "cost_saved_usd": cached_response.get("cost_saved_usd", 0.0),
                "latency_ms": latency_ms
            }
        
        # Cache miss - select model and make request
        task_description = self._extract_task_description(messages)
        
        routing_decision = await self.select_model(
            task_description=task_description,
            task_type=task_type,
            **kwargs
        )
        
        # Make API call (placeholder - would integrate with actual API clients)
        response_content, actual_tokens, actual_latency = await self._call_model_api(
            messages=messages,
            model_id=routing_decision.selected_model,
            provider_name=routing_decision.provider_name
        )
        
        # Track API call
        tracking_result = await self.cost_tracker.track_api_call(
            provider_name=routing_decision.provider_name,
            model_id=routing_decision.selected_model,
            input_tokens=actual_tokens["input"],
            output_tokens=actual_tokens["output"],
            latency_ms=actual_latency,
            agent_id=agent_id
        )
        
        # Cache the response
        await self.cache_service.set_semantic_cache(
            query_text=query_text,
            response_text=response_content,
            model_used=routing_decision.selected_model,
            tokens_saved=0,  # Would calculate based on typical response length
            confidence_score=0.9,
            agent_id=agent_id
        )
        
        return {
            "content": response_content,
            "model_used": routing_decision.selected_model,
            "cached": False,
            "routing_decision": routing_decision.to_dict(),
            "cost_usd": tracking_result.get("cost_usd", 0.0),
            "latency_ms": actual_latency,
            "input_tokens": actual_tokens["input"],
            "output_tokens": actual_tokens["output"]
        }
    
    def _messages_to_text(self, messages: List[Dict[str, str]]) -> str:
        """Convert messages to a single query text for caching."""
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
    
    def _extract_task_description(self, messages: List[Dict[str, str]]) -> str:
        """Extract task description from messages."""
        if not messages:
            return ""
        
        # Use the last user message as task description
        for msg in reversed(messages):
            if msg["role"] == "user":
                return msg["content"]
        
        return messages[-1]["content"]
    
    async def _call_model_api(
        self,
        messages: List[Dict[str, str]],
        model_id: str,
        provider_name: str
    ) -> Tuple[str, Dict[str, int], int]:
        """
        Call the actual model API (placeholder implementation).
        
        In a real implementation, this would integrate with:
        - OpenAI-compatible clients (for DeepSeek, Groq, etc.)
        - Anthropic SDK
        - Ollama API
        """
        # Placeholder - simulate API call
        await asyncio.sleep(0.1)
        
        # Simulate response based on model
        model_config = self.config.models.get(model_id)
        if model_config:
            quality = model_config.quality_score
        else:
            quality = 0.5
        
        # Simulate token counts
        input_text = self._messages_to_text(messages)
        input_tokens = len(input_text) // 4
        
        # Simulate response
        if "summar" in input_text.lower():
            response = "This is a simulated summary of the input text."
        elif "translate" in input_text.lower():
            response = "This is a simulated translation."
        elif "code" in input_text.lower():
            response = "```python\nprint('Simulated code generation')\n```"
        else:
            response = f"This is a simulated response from {model_id}. The model has quality score {quality:.2f}."
        
        output_tokens = len(response) // 4
        
        # Simulate latency based on provider
        if provider_name == "groq":
            latency = 500  # ms
        elif provider_name == "ollama":
            latency = 2000  # ms
        elif provider_name == "deepseek":
            latency = 1500  # ms
        elif provider_name == "anthropic":
            latency = 3000  # ms
        else:
            latency = 1000  # ms
        
        return response, {"input": input_tokens, "output": output_tokens}, latency

# Global model router instance
model_router = ModelRouter()

async def initialize_model_router():
    """Initialize the model router."""
    await model_router.initialize()

async def close_model_router():
    """Close the model router."""
    await model_router.close()

if __name__ == "__main__":
    # Test the model router
    async def test():
        await initialize_model_router()
        
        # Test model selection
        decision = await model_router.select_model(
            task_description="Summarize this document about climate change",
            task_type="summarization"
        )
        print("Model Selection Decision:", json.dumps(decision.to_dict(), indent=2))
        
        # Test request processing
        messages = [
            {"role": "user", "content": "What is the capital of France?"}
        ]
        response = await model_router.process_request(messages, task_type="simple_query", agent_id=None)
        print("\nRequest Response:", json.dumps(response, indent=2))
        
        await close_model_router()
    
    asyncio.run(test())
