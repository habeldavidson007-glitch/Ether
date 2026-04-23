"""
Chain-of-Thought Reasoning for Ether AI
Provides step-by-step reasoning for complex queries.
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
import re


@dataclass
class ReasoningStep:
    """A single step in the reasoning chain."""
    step_number: int
    description: str
    reasoning: str
    conclusion: Optional[str] = None
    confidence: float = 1.0


@dataclass
class ReasoningResult:
    """Complete reasoning chain with final answer."""
    question: str
    steps: List[ReasoningStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    confidence: float = 0.0
    success: bool = False


class ChainOfThoughtReasoner:
    """
    Chain-of-thought reasoner for breaking down complex problems.
    Provides structured step-by-step analysis.
    """

    def __init__(self):
        self.step_handlers: Dict[str, Callable] = {}
        self.max_steps = 10
        self.min_confidence = 0.3

    def register_handler(self, problem_type: str, handler: Callable):
        """Register a handler for a specific problem type."""
        self.step_handlers[problem_type] = handler

    def reason(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        max_steps: Optional[int] = None
    ) -> ReasoningResult:
        """
        Perform chain-of-thought reasoning on a question.
        
        Args:
            question: The question or problem to solve
            context: Additional context information
            max_steps: Maximum number of reasoning steps
            
        Returns:
            ReasoningResult with steps and final answer
        """
        result = ReasoningResult(question=question)
        steps_limit = max_steps or self.max_steps
        
        # Analyze question type
        question_type = self._classify_question(question)
        
        # Generate reasoning steps
        current_step = 0
        working_memory: Dict[str, Any] = {"question": question, "context": context or {}}
        
        while current_step < steps_limit:
            step = self._generate_step(
                step_number=current_step + 1,
                question_type=question_type,
                working_memory=working_memory,
                previous_steps=result.steps
            )
            
            if step is None:
                break
            
            result.steps.append(step)
            current_step += 1
            
            # Update working memory
            if step.conclusion:
                working_memory[f"step_{current_step}"] = step.conclusion
            
            # Check if we have enough information for final answer
            if self._should_conclude(result.steps, working_memory):
                break
        
        # Generate final answer
        if result.steps:
            final_answer, confidence = self._synthesize_answer(
                question=question,
                steps=result.steps,
                working_memory=working_memory
            )
            
            result.final_answer = final_answer
            result.confidence = confidence
            result.success = confidence >= self.min_confidence
        
        return result

    def _classify_question(self, question: str) -> str:
        """Classify the type of question."""
        question_lower = question.lower()
        
        # Check for coding-related questions
        if any(keyword in question_lower for keyword in [
            'code', 'function', 'variable', 'script', 'gdscript', 'python',
            'error', 'bug', 'fix', 'implement', 'method', 'class'
        ]):
            return 'coding'
        
        # Check for math/logic questions
        if any(keyword in question_lower for keyword in [
            'calculate', 'compute', 'math', 'equation', 'formula',
            'prove', 'logic', 'theorem'
        ]):
            return 'math_logic'
        
        # Check for explanation questions
        if any(keyword in question_lower for keyword in [
            'explain', 'what is', 'how does', 'why', 'describe',
            'define', 'concept', 'meaning'
        ]):
            return 'explanation'
        
        # Check for comparison questions
        if any(keyword in question_lower for keyword in [
            'compare', 'difference', 'vs', 'versus', 'better', 'worse'
        ]):
            return 'comparison'
        
        # Default to general reasoning
        return 'general'

    def _generate_step(
        self,
        step_number: int,
        question_type: str,
        working_memory: Dict[str, Any],
        previous_steps: List[ReasoningStep]
    ) -> Optional[ReasoningStep]:
        """Generate a single reasoning step."""
        
        # Use custom handler if available
        if question_type in self.step_handlers:
            try:
                handler_result = self.step_handlers[question_type](
                    step_number=step_number,
                    working_memory=working_memory,
                    previous_steps=previous_steps
                )
                if handler_result:
                    return ReasoningStep(
                        step_number=step_number,
                        **handler_result
                    )
            except Exception:
                pass
        
        # Default step generation based on question type
        if question_type == 'coding':
            return self._generate_coding_step(step_number, working_memory, previous_steps)
        elif question_type == 'math_logic':
            return self._generate_math_step(step_number, working_memory, previous_steps)
        elif question_type == 'explanation':
            return self._generate_explanation_step(step_number, working_memory, previous_steps)
        elif question_type == 'comparison':
            return self._generate_comparison_step(step_number, working_memory, previous_steps)
        else:
            return self._generate_general_step(step_number, working_memory, previous_steps)

    def _generate_coding_step(
        self,
        step_number: int,
        working_memory: Dict[str, Any],
        previous_steps: List[ReasoningStep]
    ) -> ReasoningStep:
        """Generate a coding-related reasoning step."""
        question = working_memory.get("question", "")
        
        if step_number == 1:
            return ReasoningStep(
                step_number=step_number,
                description="Analyze the code structure and identify the issue",
                reasoning="First, I need to understand what the code is trying to do and where it might be failing.",
                conclusion="Identified key components and potential failure points."
            )
        elif step_number == 2:
            return ReasoningStep(
                step_number=step_number,
                description="Check for common patterns and best practices",
                reasoning="Review the code against Godot/GDScript best practices and common patterns.",
                conclusion="Found deviations from expected patterns."
            )
        else:
            return ReasoningStep(
                step_number=step_number,
                description="Formulate solution approach",
                reasoning="Based on the analysis, determine the most appropriate fix or implementation.",
                conclusion="Solution strategy identified."
            )

    def _generate_math_step(
        self,
        step_number: int,
        working_memory: Dict[str, Any],
        previous_steps: List[ReasoningStep]
    ) -> ReasoningStep:
        """Generate a math/logic reasoning step."""
        return ReasoningStep(
            step_number=step_number,
            description=f"Break down the problem into component {step_number}",
            reasoning="Analyzing the mathematical or logical components systematically.",
            conclusion=f"Component {step_number} analyzed."
        )

    def _generate_explanation_step(
        self,
        step_number: int,
        working_memory: Dict[str, Any],
        previous_steps: List[ReasoningStep]
    ) -> ReasoningStep:
        """Generate an explanation reasoning step."""
        if step_number == 1:
            return ReasoningStep(
                step_number=step_number,
                description="Define key concepts",
                reasoning="Start by defining the fundamental concepts involved.",
                conclusion="Key concepts identified and defined."
            )
        elif step_number == 2:
            return ReasoningStep(
                step_number=step_number,
                description="Explain relationships",
                reasoning="Describe how the concepts relate to each other.",
                conclusion="Relationships between concepts clarified."
            )
        else:
            return ReasoningStep(
                step_number=step_number,
                description="Provide examples",
                reasoning="Illustrate with concrete examples to aid understanding.",
                conclusion="Examples provided for clarity."
            )

    def _generate_comparison_step(
        self,
        step_number: int,
        working_memory: Dict[str, Any],
        previous_steps: List[ReasoningStep]
    ) -> ReasoningStep:
        """Generate a comparison reasoning step."""
        if step_number == 1:
            return ReasoningStep(
                step_number=step_number,
                description="Identify comparison criteria",
                reasoning="Determine the relevant dimensions for comparison.",
                conclusion="Comparison criteria established."
            )
        elif step_number == 2:
            return ReasoningStep(
                step_number=step_number,
                description="Analyze first option",
                reasoning="Evaluate the first option against the criteria.",
                conclusion="First option analyzed."
            )
        elif step_number == 3:
            return ReasoningStep(
                step_number=step_number,
                description="Analyze second option",
                reasoning="Evaluate the second option against the criteria.",
                conclusion="Second option analyzed."
            )
        else:
            return ReasoningStep(
                step_number=step_number,
                description="Synthesize comparison",
                reasoning="Compare the options and highlight key differences.",
                conclusion="Comparison complete."
            )

    def _generate_general_step(
        self,
        step_number: int,
        working_memory: Dict[str, Any],
        previous_steps: List[ReasoningStep]
    ) -> ReasoningStep:
        """Generate a general reasoning step."""
        return ReasoningStep(
            step_number=step_number,
            description=f"Analyze aspect {step_number} of the problem",
            reasoning="Breaking down the problem systematically to understand all aspects.",
            conclusion=f"Aspect {step_number} analyzed."
        )

    def _should_conclude(
        self,
        steps: List[ReasoningStep],
        working_memory: Dict[str, Any]
    ) -> bool:
        """Determine if we have enough information to conclude."""
        if len(steps) < 2:
            return False
        
        # Check if we have conclusions from recent steps
        recent_conclusions = [s.conclusion for s in steps[-2:] if s.conclusion]
        return len(recent_conclusions) >= 2

    def _synthesize_answer(
        self,
        question: str,
        steps: List[ReasoningStep],
        working_memory: Dict[str, Any]
    ) -> tuple:
        """Synthesize final answer from reasoning steps."""
        # Collect all conclusions
        conclusions = [s.conclusion for s in steps if s.conclusion]
        
        if not conclusions:
            return "Unable to determine answer based on available information.", 0.2
        
        # Calculate confidence based on number of steps and their confidence
        avg_confidence = sum(s.confidence for s in steps) / len(steps)
        step_bonus = min(0.3, len(steps) * 0.05)
        final_confidence = min(1.0, avg_confidence + step_bonus)
        
        # Construct answer
        answer_parts = []
        for i, step in enumerate(steps):
            if step.conclusion:
                answer_parts.append(f"({i+1}) {step.conclusion}")
        
        final_answer = " | ".join(answer_parts)
        
        return final_answer, final_confidence
