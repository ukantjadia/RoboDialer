# DeepSeek adapter and verifier
import logging
import json
import asyncio
import os
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List ,AsyncGenerator
import aiohttp
from dataclasses import dataclass, asdict

# Import agentic logging
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentic_logging import get_agentic_logger

logger = get_agentic_logger('llm')



@dataclass
class APIResponse:
    """Structured API response"""
    content: str
    status: str
    usage: Dict[str, int]
    model: str
    validation_result: Dict[str, Any]
    fallback_used: bool
    timestamp: datetime
    execution_time: float

class DeepSeekClient:
    """
    Enhanced DeepSeek LLM client with real API integration, fallback mechanism,
    response validation, and usage tracking
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None, 
                 base_url: Optional[str] = None,
                 fallback_to_mock: bool = True,
                 model: Optional[str] = None):
        # Environment-based configuration
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.fallback_to_mock = fallback_to_mock if fallback_to_mock is not None else os.getenv("ENABLE_MOCK_FALLBACK", "false").lower() == "true"
        
        # API configuration
        self.timeout = int(os.getenv("DEEPSEEK_TIMEOUT", "60"))  # Reduced from 120 to 60 seconds
        self.max_retries = int(os.getenv("DEEPSEEK_MAX_RETRIES", "5"))  # Increased retries
        
        # Rate limiting configuration
        self.requests_per_minute = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "20"))
        self.requests_per_hour = int(os.getenv("RATE_LIMIT_REQUESTS_PER_HOUR", "500"))
        self.backoff_base = float(os.getenv("RATE_LIMIT_BACKOFF_BASE", "2"))
        self.max_backoff = int(os.getenv("RATE_LIMIT_MAX_BACKOFF", "300"))
        
        # Rate limiting tracking
        self._request_times = []
        self._last_request_time = None
        self._consecutive_failures = 0
        
        # Session management
        self.session = None
        
        logger.info(f"DeepSeek client initialized - API Key: {'***' if self.api_key else 'None'}, "
                   f"Fallback enabled: {self.fallback_to_mock}, "
                   f"Rate limits: {self.requests_per_minute}/min, {self.requests_per_hour}/hour")
    
    async def __aenter__(self):
        """
        Async context manager entry
        """
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit
        """
        if self.session:
            await self.session.close()
            self.session = None
    
    async def generate_response(self, prompt: str, system_message: Optional[str] = None) -> APIResponse:
        """
        Generate response from DeepSeek with enhanced error handling and fallback
        Maintains backward compatibility with single-message requests
        """
        # Convert single prompt to message array format for internal consistency
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        # Use the context-aware method internally
        return await self.generate_response_with_context(messages)
    
    async def generate_response_with_context(
        self, 
        messages: List[Dict[str, str]], 
        system_message: Optional[str] = None
    ) -> APIResponse:
        """
        Generate response from DeepSeek using conversation context with message arrays
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            system_message: Optional system message to prepend (if not already in messages)
        
        Returns:
            APIResponse with the generated content and metadata
        """
        start_time = datetime.now()
        fallback_used = False
        created_session = False
        
        try:
            logger.info(f"Generating context-aware response from DeepSeek with {len(messages)} messages")
            
            # Validate message array format
            validated_messages = self._validate_message_array(messages, system_message)
            
            # Ensure session exists (lazily initialize if needed)
            if self.session is None:
                self.session = aiohttp.ClientSession()
                created_session = True
            
            # Try real API if key is available
            if self.api_key and self.api_key != "mock_key_for_development":
                try:
                    result = await self._call_real_api_with_messages(validated_messages)
                    execution_time = (datetime.now() - start_time).total_seconds()
                    
                    # Validate response
                    validation_result = await self.validate_response(result["content"])
                    
                    # Raw LLM logging
                    try:
                        log_full = os.getenv("LOG_LLM_RAW", "false").lower() == "true"
                        if log_full:
                            logger.info(f"[LLM][DeepSeek] raw: {result['content']}")
                        else:
                            snippet = result["content"] if len(result["content"]) <= 500 else result["content"][:500] + "..."
                            logger.debug(f"[LLM][DeepSeek] raw (truncated): {snippet}")
                    except Exception:
                        pass
                    
                    return APIResponse(
                        content=result["content"],
                        status=result["status"],
                        usage=result.get("usage", {}),
                        model=result.get("model", "deepseek-chat"),
                        validation_result=validation_result,
                        fallback_used=False,
                        timestamp=start_time,
                        execution_time=execution_time
                    )
                    
                except Exception as api_error:
                    logger.error(f"DeepSeek API call failed: {str(api_error)}")
                    execution_time = (datetime.now() - start_time).total_seconds()
                    
                    return APIResponse(
                        content=f"DeepSeek API failed: {str(api_error)}",
                        status="error",
                        usage={},
                        model="deepseek-chat",
                        validation_result={"is_valid": False, "errors": [str(api_error)]},
                        fallback_used=False,
                        timestamp=start_time,
                        execution_time=execution_time
                    )
            else:
                logger.error("No DeepSeek API key configured")
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return APIResponse(
                    content="DeepSeek API key not configured",
                    status="error",
                    usage={},
                    model="deepseek-chat",
                    validation_result={"is_valid": False, "errors": ["No API key configured"]},
                    fallback_used=False,
                    timestamp=start_time,
                    execution_time=execution_time
                )
            
        except Exception as e:
            logger.error(f"Error generating context-aware response: {str(e)}")
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return APIResponse(
                content=f"Error generating response: {str(e)}",
                status="error",
                usage={},
                model="deepseek-chat",
                validation_result={"is_valid": False, "errors": [str(e)]},
                fallback_used=fallback_used,
                timestamp=start_time,
                execution_time=execution_time
            )
        finally:
            # Don't close session here to avoid CancelledError
            # Session will be closed when the client is properly disposed
            pass
    async def stream_response(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Generates a streaming response using Server-Sent Events.
        Yields text chunks as they arrive from the API.
        """
        if not self.api_key:
            logger.error("Cannot stream response: DeepSeek API key not configured.")
            yield "Error: DeepSeek API key not configured."
            return

        # Use the existing validation helper
        messages = self._validate_message_array([{"role": "user", "content": prompt}])
        
        # Ensure aiohttp session exists
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "LeadGenAI-AgenticBackend/1.0"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True  # This is the critical flag for streaming
        }

        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with self.session.post(f"{self.base_url}/v1/chat/completions", headers=headers, json=payload, timeout=timeout) as response:
                response.raise_for_status()  # Will raise an exception for 4xx/5xx responses
                
                async for line in response.content:
                    decoded_line = line.decode("utf-8").strip()
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[len("data: "):]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, IndexError):
                            logger.warning(f"Could not parse stream chunk: {data_str}")
        except Exception as e:
            logger.error(f"Error during DeepSeek streaming call: {e}", exc_info=True)
            yield f"Error processing stream: {str(e)}"
    
    def _validate_message_array(
        self, 
        messages: List[Dict[str, str]], 
        system_message: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Validate and prepare message array for API call
        
        Args:
            messages: List of message dictionaries
            system_message: Optional system message to prepend
            
        Returns:
            Validated and properly formatted message array
            
        Raises:
            ValueError: If message format is invalid
        """
        if not messages:
            raise ValueError("Message array cannot be empty")
        
        validated_messages = []
        
        # Add system message if provided and not already present
        if system_message and (not messages or messages[0].get("role") != "system"):
            validated_messages.append({"role": "system", "content": system_message})
        
        # Validate each message
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ValueError(f"Message {i} must be a dictionary")
            
            if "role" not in msg or "content" not in msg:
                raise ValueError(f"Message {i} must have 'role' and 'content' keys")
            
            role = msg["role"]
            content = msg["content"]
            
            if role not in ["system", "user", "assistant"]:
                raise ValueError(f"Message {i} has invalid role '{role}'. Must be 'system', 'user', or 'assistant'")
            
            if not isinstance(content, str) or not content.strip():
                raise ValueError(f"Message {i} content must be a non-empty string")
            
            validated_messages.append({"role": role, "content": content.strip()})
        
        # Ensure we have at least one user message
        user_messages = [msg for msg in validated_messages if msg["role"] == "user"]
        if not user_messages:
            raise ValueError("Message array must contain at least one user message")
        
        logger.debug(f"Validated message array with {len(validated_messages)} messages")
        return validated_messages
    
    async def _check_rate_limits(self) -> Optional[float]:
        """
        Check rate limits and return wait time if needed.
        
        Returns:
            Wait time in seconds if rate limited, None otherwise
        """
        now = datetime.now()
        
        # Clean old request times (older than 1 hour)
        hour_ago = now - timedelta(hours=1)
        self._request_times = [t for t in self._request_times if t > hour_ago]
        
        # Check hourly limit
        if len(self._request_times) >= self.requests_per_hour:
            oldest_request = min(self._request_times)
            wait_time = (oldest_request + timedelta(hours=1) - now).total_seconds()
            logger.warning(f"Hourly rate limit reached ({self.requests_per_hour}/hour), waiting {wait_time:.1f}s")
            return max(wait_time, 0)
        
        # Check per-minute limit
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [t for t in self._request_times if t > minute_ago]
        
        if len(recent_requests) >= self.requests_per_minute:
            oldest_recent = min(recent_requests)
            wait_time = (oldest_recent + timedelta(minutes=1) - now).total_seconds()
            logger.warning(f"Per-minute rate limit reached ({self.requests_per_minute}/min), waiting {wait_time:.1f}s")
            return max(wait_time, 0)
        
        # Check minimum interval between requests (adaptive based on failures)
        if self._last_request_time:
            min_interval = min(self._consecutive_failures * 0.5, 5.0)  # Max 5 seconds
            time_since_last = (now - self._last_request_time).total_seconds()
            
            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                logger.debug(f"Adaptive rate limiting: waiting {wait_time:.1f}s (failures: {self._consecutive_failures})")
                return wait_time
        
        return None
    
    async def _record_request(self, success: bool = True):
        """Record a request for rate limiting purposes."""
        now = datetime.now()
        self._request_times.append(now)
        self._last_request_time = now
        
        if success:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1
    
    async def _call_real_api_with_messages(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Call actual DeepSeek API with message array and retry logic
        
        Args:
            messages: Validated list of message dictionaries
            
        Returns:
            Dictionary with response content and metadata
        """
        # Check rate limits before making request
        wait_time = await self._check_rate_limits()
        if wait_time and wait_time > 0:
            logger.info(f"Rate limiting: waiting {wait_time:.1f}s before API call")
            await asyncio.sleep(wait_time)
        
        # Lazily initialize session if needed
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "stream": False
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "LeadGenAI-AgenticBackend/1.0"
        }
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"API call attempt {attempt + 1}/{self.max_retries} with {len(messages)} messages")
                
                timeout = aiohttp.ClientTimeout(total=self.timeout, connect=10, sock_read=self.timeout)
                async with self.session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=timeout
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Validate response structure
                        if "choices" not in data or not data["choices"]:
                            await self._record_request(success=False)
                            raise Exception("Invalid API response: missing choices")
                        
                        content = data["choices"][0]["message"]["content"]
                        
                        # Record successful request
                        await self._record_request(success=True)
                        
                        logger.info(f"Context-aware API call successful with {len(messages)} messages")
                        
                        return {
                            "content": content,
                            "status": "success",
                            "usage": data.get("usage", {}),
                            "model": data.get("model", "deepseek-chat")
                        }
                    
                    elif response.status == 401:
                        error_text = await response.text()
                        raise Exception(f"Authentication failed: {error_text}")
                    
                    elif response.status == 429:
                        error_text = await response.text()
                        await self._record_request(success=False)
                        
                        if attempt < self.max_retries - 1:
                            # Enhanced exponential backoff with jitter
                            base_wait = min(self.backoff_base ** attempt, self.max_backoff)
                            jitter = random.uniform(0.1, 0.3) * base_wait
                            wait_time = base_wait + jitter
                            
                            logger.warning(f"Rate limited (429), waiting {wait_time:.1f}s before retry {attempt + 2}/{self.max_retries}")
                            await asyncio.sleep(wait_time)
                            continue
                        raise Exception(f"Rate limit exceeded after {self.max_retries} attempts: {error_text}")
                    
                    elif response.status >= 500:
                        error_text = await response.text()
                        await self._record_request(success=False)
                        
                        if attempt < self.max_retries - 1:
                            wait_time = min(self.backoff_base ** attempt, self.max_backoff)
                            logger.warning(f"Server error {response.status}, waiting {wait_time:.1f}s before retry {attempt + 2}/{self.max_retries}")
                            await asyncio.sleep(wait_time)
                            continue
                        raise Exception(f"Server error after {self.max_retries} attempts: {response.status} - {error_text}")
                    
                    else:
                        error_text = await response.text()
                        await self._record_request(success=False)
                        raise Exception(f"API call failed: {response.status} - {error_text}")
                        
            except asyncio.TimeoutError:
                await self._record_request(success=False)
                last_exception = Exception(f"API call timeout after {self.timeout}s")
                if attempt < self.max_retries - 1:
                    wait_time = min(self.backoff_base ** attempt, 10)  # Max 10s for timeouts
                    logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries}, waiting {wait_time:.1f}s before retry")
                    await asyncio.sleep(wait_time)
                    continue
                    
            except asyncio.CancelledError:
                logger.warning("Request was cancelled, likely due to timeout or client disconnection")
                await self._record_request(success=False)
                raise  # Re-raise CancelledError to properly handle cancellation
                
            except aiohttp.ClientError as e:
                await self._record_request(success=False)
                last_exception = Exception(f"Network error: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = min(self.backoff_base ** attempt, 5)  # Max 5s for network errors
                    logger.warning(f"Network error on attempt {attempt + 1}/{self.max_retries}, waiting {wait_time:.1f}s before retry")
                    await asyncio.sleep(wait_time)
                    continue
                    
            except Exception as e:
                await self._record_request(success=False)
                last_exception = e
                if attempt < self.max_retries - 1 and "Authentication" not in str(e):
                    wait_time = min(self.backoff_base ** attempt, 5)
                    logger.warning(f"Error on attempt {attempt + 1}/{self.max_retries}: {str(e)}, waiting {wait_time:.1f}s before retry")
                    await asyncio.sleep(wait_time)
                    continue
                break
        
        raise last_exception or Exception("All retry attempts failed")
    
    async def _call_real_api(self, prompt: str, system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Legacy method - converts single prompt to message array and calls new method
        Maintained for backward compatibility
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        return await self._call_real_api_with_messages(messages)
    

    
    async def validate_response(self, response: str) -> Dict[str, Any]:
        """
        Enhanced response validation with content quality checks
        """
        validation_result = {
            "is_valid": True,
            "is_json": False,
            "has_required_fields": False,
            "content_quality": "unknown",
            "errors": [],
            "warnings": []
        }
        
        try:
            # Check if response is empty or too short
            if not response or len(response.strip()) < 10:
                validation_result["is_valid"] = False
                validation_result["errors"].append("Response is empty or too short")
                return validation_result
            
            # Try to parse as JSON
            try:
                parsed = json.loads(response)
                validation_result["is_json"] = True
                
                # Check for common required fields
                required_fields = ["confidence"]
                optional_fields = ["analysis", "comparison_table", "search_results", "key_insights"]
                
                missing_required = []
                for field in required_fields:
                    if field not in parsed:
                        missing_required.append(field)
                
                if missing_required:
                    validation_result["warnings"].append(f"Missing recommended fields: {', '.join(missing_required)}")
                else:
                    validation_result["has_required_fields"] = True
                
                # Check for at least one content field
                has_content = any(field in parsed for field in optional_fields)
                if not has_content:
                    validation_result["warnings"].append("No recognized content fields found")
                
                # Validate confidence score if present
                if "confidence" in parsed:
                    confidence = parsed["confidence"]
                    if isinstance(confidence, dict) and "score" in confidence:
                        score = confidence["score"]
                        if not isinstance(score, (int, float)) or not 0 <= score <= 1:
                            validation_result["warnings"].append("Confidence score should be between 0 and 1")
                
                validation_result["content_quality"] = "good" if validation_result["has_required_fields"] and has_content else "fair"
                
            except json.JSONDecodeError:
                # Not JSON, validate as plain text
                validation_result["is_json"] = False
                
                # Check for minimum content quality
                if len(response.strip()) > 50:
                    validation_result["content_quality"] = "fair"
                else:
                    validation_result["content_quality"] = "poor"
                    validation_result["warnings"].append("Response seems too brief")
                
                # Check for common error patterns
                error_patterns = ["error", "failed", "unable", "cannot", "sorry"]
                if any(pattern in response.lower() for pattern in error_patterns):
                    validation_result["warnings"].append("Response may contain error indicators")
            
            # Final validation
            if validation_result["errors"]:
                validation_result["is_valid"] = False
            
            return validation_result
            
        except Exception as e:
            return {
                "is_valid": False,
                "is_json": False,
                "has_required_fields": False,
                "content_quality": "error",
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
    


# Standalone execution
async def main():
    """
    Enhanced standalone execution for testing all new features including context support
    """
    # Test with environment variables (will fallback to mock if no API key)
    async with DeepSeekClient() as client:
        print("=== DeepSeek Client Testing ===")
        print(f"API Key configured: {'Yes' if client.api_key and client.api_key != 'mock_key_for_development' else 'No (using mock)'}")
        print(f"Fallback enabled: {client.fallback_to_mock}")
        print()
        
        # Test 1: Basic response generation (backward compatibility)
        print("Test 1: Basic response generation (backward compatibility)")
        prompt = "Compare lead_2 and lead_3 and tell which has better growth potential"
        response = await client.generate_response(prompt)
        
        print(f"Status: {response.status}")
        print(f"Fallback used: {response.fallback_used}")
        print(f"Execution time: {response.execution_time:.2f}s")
        print(f"Validation: {response.validation_result}")
        print(f"Content preview: {response.content[:200]}...")
        print()
        
        # Test 2: Context-aware conversation
        print("Test 2: Context-aware conversation")
        conversation_messages = [
            {"role": "system", "content": "You are a helpful AI assistant for lead generation and business analysis."},
            {"role": "user", "content": "What are the key factors to consider when evaluating a lead?"},
            {"role": "assistant", "content": "Key factors include company size, industry, growth potential, decision-maker accessibility, and budget alignment."},
            {"role": "user", "content": "Can you elaborate on the growth potential factor?"}
        ]
        
        context_response = await client.generate_response_with_context(conversation_messages)
        print(f"Context status: {context_response.status}")
        print(f"Execution time: {context_response.execution_time:.2f}s")
        print(f"Content preview: {context_response.content[:200]}...")
        print()
        
        # Test 3: Context with system message override
        print("Test 3: Context with system message override")
        user_messages = [
            {"role": "user", "content": "Hello, I need help with lead scoring."},
            {"role": "assistant", "content": "I'd be happy to help with lead scoring. What specific aspect would you like to focus on?"},
            {"role": "user", "content": "How do I prioritize leads based on engagement?"}
        ]
        
        override_response = await client.generate_response_with_context(
            user_messages, 
            system_message="You are a specialized lead scoring expert with 10 years of experience."
        )
        print(f"Override status: {override_response.status}")
        print(f"Content preview: {override_response.content[:200]}...")
        print()
        
        # Test 4: Error handling - empty message array
        print("Test 4: Error handling - empty message array")
        try:
            empty_response = await client.generate_response_with_context([])
            print(f"Empty array handled: {empty_response.status}")
        except Exception as e:
            print(f"Exception caught: {str(e)}")
        print()
        
        # Test 5: Error handling - invalid message format
        print("Test 5: Error handling - invalid message format")
        try:
            invalid_messages = [
                {"role": "invalid_role", "content": "This should fail"},
                {"role": "user", "content": ""}  # Empty content
            ]
            invalid_response = await client.generate_response_with_context(invalid_messages)
            print(f"Invalid format handled: {invalid_response.status}")
        except Exception as e:
            print(f"Exception caught: {str(e)}")
        print()
        
        # Test 6: Backward compatibility with system message
        print("Test 6: Backward compatibility with system message")
        compat_response = await client.generate_response(
            "Analyze the financial performance of TechCorp Inc.",
            system_message="You are a financial analyst."
        )
        print(f"Compatibility status: {compat_response.status}")
        print(f"Content quality: {compat_response.validation_result.get('content_quality', 'unknown')}")
        print()
        
        print("=== Testing Complete ===")

if __name__ == "__main__":
    # Set up basic logging for testing
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(main()) 