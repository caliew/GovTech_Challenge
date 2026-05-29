import re
import json
import logging
from typing import Dict, List, Any, Callable, Tuple
from backend.app.utils.llm import llm_service

logger = logging.getLogger("BaseAgent")

class BaseAgent:
    def __init__(self, name: str, system_instruction: str, ws_callback: Callable = None):
        self.name = name
        self.system_instruction = system_instruction
        self.tools: Dict[str, Tuple[Callable, str]] = {}  # {tool_name: (tool_func, tool_desc)}
        self.ws_callback = ws_callback

    def register_tool(self, name: str, func: Callable, description: str):
        """Registers a tool with its function and usage description."""
        self.tools[name] = (func, description)
        logger.info(f"🔵🟣 [{self.name}] Registered tool: {name} 🟣🔵")

    async def log_step(self, step_type: str, content: str):
        """Helper to print logs and push updates to WebSockets."""
        if self.ws_callback:
            await self.ws_callback({
                "agent": self.name,
                "type": step_type,  # thought, action, observation, status, result
                "content": content
            })

    def _get_tools_description(self) -> str:
        """Formulates instructions of available tools for the LLM."""
        desc = ""
        for name, (_, d) in self.tools.items():
            desc += f"- **{name}**: {d}\n"
        return desc

    def _build_react_prompt(self, user_query: str, history: List[Dict[str, str]]) -> str:
        """Creates the formal ReAct instruction set."""
        tools_str = self._get_tools_description()
        
        prompt = f"""
You are the {self.name} Agent. You operate using the ReAct (Reasoning, Action, Observation) pattern.
Your goal is to solve the following objective:
"{user_query}"

You have access to the following tools:
{tools_str if tools_str else "- No tools available."}

To use a tool, you MUST output a response strictly in this format:
Thought: Your internal logical reasoning about what to do next.
Action: The exact tool name to call (must be one of the registered tools).
Action Input: The arguments to pass to the tool (as a raw string or JSON).

When you have completed your task and gathered all necessary data, output in this format:
Thought: I have finished my task and have all findings.
Final Answer: [Your complete, structured response here]

---
Reasoning History:
"""
        for step in history:
            prompt += f"\nThought: {step['thought']}\n"
            if step.get("action"):
                prompt += f"Action: {step['action']}\n"
                prompt += f"Action Input: {step['action_input']}\n"
                prompt += f"Observation: {step['observation']}\n"
                
        prompt += "\nNext step:"
        return prompt

    def _parse_react_response(self, text: str) -> Tuple[str, str, str]:
        """Parses the ReAct text from LLM response into Thought, Action, and Action Input."""
        thought = ""
        action = ""
        action_input = ""

        # Extract Thought
        thought_match = re.search(r"Thought:(.*?)(?:Action:|Final Answer:|$)", text, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()
        else:
            thought = text.strip()  # If no thought structure, treat whole response as reasoning

        # Check for Final Answer
        final_match = re.search(r"Final Answer:(.*)", text, re.DOTALL | re.IGNORECASE)
        if final_match:
            # We reached final answer
            return thought, "FINAL_ANSWER", final_match.group(1).strip()

        # Extract Action & Action Input
        action_match = re.search(r"Action:(.*?)(?:Action Input:|$)", text, re.DOTALL | re.IGNORECASE)
        action_input_match = re.search(r"Action Input:(.*)", text, re.DOTALL | re.IGNORECASE)

        if action_match:
            action = action_match.group(1).strip()
        if action_input_match:
            action_input = action_input_match.group(1).strip()

        return thought, action, action_input

    async def run(self, user_query: str, max_iterations: int = 6) -> str:
        """Executes the ReAct loop iteratively."""
        logger.info(f"🔵🔵 BASE RUN [{self.name}] [{max_iterations}] 🔵🔵")
        await self.log_step("status", f"Activated. Analyzing query: {user_query}")
        history = []

        for i in range(max_iterations):
            prompt = self._build_react_prompt(user_query, history)
            
            # Generate reasoning using LLM
            logger.info(f"🔵🔵 BASE RUN [{self.name}] REASONING START [{i+1}/{max_iterations}] 🔵🔵")
            await self.log_step("status", f"Reasoning (Step {i+1}/{max_iterations})...")
            response = llm_service.generate(prompt, self.system_instruction)
            
            # Parse response
            thought, action, action_input = self._parse_react_response(response)
            await self.log_step("thought", thought)
            logger.info(f"🔵🔵 BASE RUN [{self.name}] THOUGHT <{thought}> 🔵🔵")
            logger.info(f"🔵🔵 BASE RUN [{self.name}] ACTION <{action}> 🔵🔵")

            if action == "FINAL_ANSWER":
                await self.log_step("result", action_input)
                await self.log_step("status", "Task completed.")
                return action_input

            if not action:
                # If no tool specified, but not marked Final Answer, ask LLM to wrap up next iteration
                await self.log_step("status", "No action specified. Transitioning to conclusion.")
                logger.info(f"🔵🔵 BASE RUN [{self.name}] NO ACTION 🔵🔵")
                history.append({
                    "thought": thought,
                    "action": "FINAL_ANSWER",
                    "action_input": "",
                    "observation": "Please summarize your findings into a Final Answer."
                })
                continue

            # Execute Tool
            await self.log_step("action", f"🔵🔵 Calling tool [{action}] with inputs: {action_input}")
            
            observation = ""
            if action in self.tools:
                tool_func, _ = self.tools[action]
                try:
                    # Run the tool synchronously
                    observation = tool_func(action_input)
                except Exception as e:
                    observation = f"Error executing tool: {str(e)}"
            else:
                observation = f"Error: Tool '{action}' is not registered. Registered: {list(self.tools.keys())}"

            await self.log_step("observation", str(observation))

            # Store history
            history.append({
                "thought": thought,
                "action": action,
                "action_input": action_input,
                "observation": str(observation)
            })

        await self.log_step("status", "Limit reached. Compiling final findings.")
        return "ReAct loop reached iteration threshold. Results are incomplete."
