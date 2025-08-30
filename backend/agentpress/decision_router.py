"""
Adaptive Mode Decision Router for AgentPress.

This module implements intelligent routing between direct LLM responses and agentic tool-based responses.
It analyzes user input to determine whether a simple LLM response is sufficient or if the request
requires tool usage and agent orchestration.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from utils.logger import logger


@dataclass
class RoutingDecision:
    """Result of routing decision analysis."""
    mode: str  # "direct" or "agentic"
    reason: str
    confidence: float  # 0.0 to 1.0


class DecisionRouter:
    """
    Intelligent router that determines whether user input should be handled
    by direct LLM response or agentic tool-based processing.
    """
    
    def __init__(self):
        # Keywords that strongly indicate tool usage
        self.agentic_verbs = {
            'create', 'make', 'build', 'generate', 'write', 'save', 'download',
            'search', 'find', 'lookup', 'browse', 'crawl', 'fetch', 'get',
            'execute', 'run', 'install', 'deploy', 'launch', 'start',
            'convert', 'transform', 'process', 'analyze', 'calculate',
            'send', 'email', 'post', 'upload', 'share', 'publish',
            'edit', 'modify', 'update', 'change', 'delete', 'remove',
            'code', 'program', 'script', 'develop', 'implement',
            'test', 'debug', 'fix', 'solve', 'troubleshoot'
        }
        
        # File-related keywords
        self.file_keywords = {
            'file', 'document', 'pdf', 'docx', 'txt', 'csv', 'json', 'xml',
            'image', 'photo', 'picture', 'video', 'audio', 'presentation',
            'spreadsheet', 'report', 'folder', 'directory'
        }
        
        # Web-related keywords
        self.web_keywords = {
            'website', 'webpage', 'url', 'link', 'http', 'https', 'www',
            'google', 'search', 'browse', 'crawl', 'scrape', 'api'
        }
        
        # Direct response indicators
        self.direct_patterns = [
            r'^(hi|hello|hey|good morning|good afternoon|good evening)',
            r'^(how are you|what\'s up|how\'s it going)',
            r'^(what is|what are|who is|who are|when is|when are|where is|where are|why is|why are|how is|how are)',
            r'^(explain|tell me about|describe)',
            r'^(thanks|thank you|bye|goodbye|see you)',
            r'(what\'s \d+[\+\-\*\/]\d+|what is \d+[\+\-\*\/]\d+)',
        ]
        
        # Multi-step indicators
        self.multi_step_keywords = {
            'then', 'after', 'next', 'also', 'and then', 'followed by',
            'step', 'steps', 'process', 'workflow', 'pipeline'
        }

    def classify_input(
        self, 
        user_text: str, 
        context: Optional[List[Dict[str, Any]]] = None,
        flags: Optional[Dict[str, Any]] = None
    ) -> RoutingDecision:
        """
        Classify user input as requiring direct or agentic response.
        
        Args:
            user_text: The user's input text
            context: Optional context from last 3 messages
            flags: Optional flags for routing decisions
            
        Returns:
            RoutingDecision with mode, reason, and confidence
        """
        try:
            text_lower = user_text.lower().strip()
            
            # Quick checks for obvious direct responses
            if self._is_greeting_or_simple_qa(text_lower):
                return RoutingDecision(
                    mode="direct",
                    reason="Simple greeting, small talk, or basic Q&A",
                    confidence=0.9
                )
            
            # Check for explicit tool usage indicators
            agentic_score = self._calculate_agentic_score(text_lower)
            
            # Check for multi-step complexity
            complexity_score = self._calculate_complexity_score(text_lower)
            
            # Check length and structure
            length_score = self._calculate_length_score(user_text)
            
            # Combine scores
            total_agentic_score = agentic_score + complexity_score + length_score
            
            # Make decision based on combined score
            if total_agentic_score >= 0.6:
                return RoutingDecision(
                    mode="agentic",
                    reason=f"High tool usage indicators (score: {total_agentic_score:.2f})",
                    confidence=min(total_agentic_score, 0.95)
                )
            elif total_agentic_score <= 0.3:
                return RoutingDecision(
                    mode="direct",
                    reason=f"Low tool usage indicators (score: {total_agentic_score:.2f})",
                    confidence=1.0 - total_agentic_score
                )
            else:
                # Borderline case - use conservative approach
                return RoutingDecision(
                    mode="agentic",
                    reason=f"Borderline case, defaulting to agentic (score: {total_agentic_score:.2f})",
                    confidence=0.5
                )
                
        except Exception as e:
            logger.error(f"Error in input classification: {e}")
            # Default to agentic on error to be safe
            return RoutingDecision(
                mode="agentic",
                reason="Error in classification, defaulting to agentic",
                confidence=0.5
            )

    def _is_greeting_or_simple_qa(self, text_lower: str) -> bool:
        """Check if input is a simple greeting or basic Q&A."""
        # Check direct patterns
        for pattern in self.direct_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Check for simple math
        if re.search(r'what\'s \d+[\+\-\*\/]\d+|what is \d+[\+\-\*\/]\d+', text_lower):
            return True
            
        # Check for very short questions
        if len(text_lower.split()) <= 5 and '?' in text_lower:
            # But exclude questions that might need tools
            if not any(keyword in text_lower for keyword in self.agentic_verbs):
                return True
        
        return False

    def _calculate_agentic_score(self, text_lower: str) -> float:
        """Calculate score based on agentic keywords and patterns."""
        score = 0.0
        words = text_lower.split()
        
        # Check for agentic verbs
        verb_matches = sum(1 for word in words if word in self.agentic_verbs)
        score += min(verb_matches * 0.3, 0.6)
        
        # Check for file-related keywords
        file_matches = sum(1 for word in words if word in self.file_keywords)
        score += min(file_matches * 0.2, 0.4)
        
        # Check for web-related keywords
        web_matches = sum(1 for word in words if word in self.web_keywords)
        score += min(web_matches * 0.2, 0.4)
        
        # Check for specific patterns that indicate tool usage
        if re.search(r'(create|make|generate).*?(file|document|pdf|image|video)', text_lower):
            score += 0.4
        
        if re.search(r'(search|find|lookup).*?(web|internet|online)', text_lower):
            score += 0.4
            
        if re.search(r'(run|execute).*?(command|script|code)', text_lower):
            score += 0.4
        
        return min(score, 1.0)

    def _calculate_complexity_score(self, text_lower: str) -> float:
        """Calculate score based on multi-step complexity indicators."""
        score = 0.0
        
        # Check for multi-step keywords
        multi_step_matches = sum(1 for keyword in self.multi_step_keywords if keyword in text_lower)
        score += min(multi_step_matches * 0.2, 0.4)
        
        # Check for multiple sentences (potential multi-step)
        sentence_count = len([s for s in text_lower.split('.') if s.strip()])
        if sentence_count > 2:
            score += 0.2
        
        # Check for lists or numbered steps
        if re.search(r'(\d+\.|•|\*|\-)\s', text_lower):
            score += 0.3
        
        return min(score, 1.0)

    def _calculate_length_score(self, text: str) -> float:
        """Calculate score based on text length and structure."""
        word_count = len(text.split())
        
        # Very short texts are likely direct
        if word_count <= 5:
            return 0.0
        
        # Medium texts might be either
        if word_count <= 15:
            return 0.1
        
        # Longer texts are more likely to be complex
        if word_count <= 30:
            return 0.2
        
        # Very long texts are likely complex
        return 0.3

    def should_use_direct_mode(
        self, 
        user_text: str, 
        context: Optional[List[Dict[str, Any]]] = None,
        flags: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Convenience method to determine if direct mode should be used.
        
        Returns:
            Tuple of (use_direct, reason)
        """
        decision = self.classify_input(user_text, context, flags)
        return decision.mode == "direct", decision.reason

    def should_use_agentic_mode(
        self, 
        user_text: str, 
        context: Optional[List[Dict[str, Any]]] = None,
        flags: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Convenience method to determine if agentic mode should be used.
        
        Returns:
            Tuple of (use_agentic, reason)
        """
        decision = self.classify_input(user_text, context, flags)
        return decision.mode == "agentic", decision.reason


    def should_use_agent_mode(self, query: str) -> bool:
        """
        Determine if a query should use agent mode.
        
        Args:
            query: User query to analyze
            
        Returns:
            True if agent mode should be used, False for direct mode
        """
        use_agentic, _ = self.should_use_agentic_mode(query)
        return use_agentic

