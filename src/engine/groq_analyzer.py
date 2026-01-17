import os
from groq import Groq
import json

class GroqAnalyzer:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def analyze_impact(self, filename: str, affected_nodes: list, changes: str = "", code_context: str = ""):
        """
        Uses Groq (LLaMA-3) to perform a "Reasoned Impact Analysis".
        Returns a structured JSON response with affected files, functions, and line numbers.
        """
        if not affected_nodes:
            return {
                "impact_level": "none",
                "summary": f"No downstream dependencies found for {filename}. This change is isolated.",
                "changed_file": filename,
                "affected_items": [],
                "recommendations": []
            }

        # Prepare affected nodes summary for the prompt
        affected_summary = []
        for node in affected_nodes:
            affected_summary.append({
                "file": node.get("file"),
                "symbol": node.get("symbol"),
                "symbol_type": node.get("symbol_type"),
                "line": node.get("line_number"),
                "depends_on": node.get("depends_on"),
                "depends_on_type": node.get("depends_on_type")
            })

        prompt = f"""You are a Senior Software Architect performing a Code Impact Analysis.

TASK: Analyze if the code changes in '{filename}' will impact the downstream dependencies listed below.

CHANGE DESCRIPTION:
{changes if changes else "No specific description provided. Assume generic logic changes."}

CODE CONTEXT:
{code_context[:1000] if code_context else "No code snippet provided."}

AFFECTED DEPENDENCIES (from Knowledge Graph):
{json.dumps(affected_summary, indent=2)}

INSTRUCTIONS:
1. Determine the impact level: "high" (breaking changes), "medium" (potential issues), "low" (minor impact), or "none" (no impact)
2. For each affected item, analyze if it will actually break or just needs attention
3. Provide specific reasoning for each affected symbol
4. Give actionable recommendations

CRITICAL: You MUST respond with ONLY valid JSON in this exact format (no markdown, no code blocks, no extra text):

{{
  "impact_level": "high|medium|low|none",
  "summary": "Brief 1-2 sentence summary of the overall impact",
  "changed_file": "{filename}",
  "affected_items": [
    {{
      "file": "path/to/file.py",
      "symbol": "function_or_class_name",
      "symbol_type": "function|class",
      "line_number": 42,
      "depends_on": "changed_symbol_name",
      "impact_reason": "Specific reason why this is affected",
      "breaking": true
    }}
  ],
  "recommendations": [
    "Specific action item 1",
    "Specific action item 2"
  ]
}}

Respond with ONLY the JSON object, nothing else."""

        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a code analysis assistant that responds ONLY with valid JSON. Never use markdown code blocks or any text outside the JSON object."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            response_text = completion.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            # Parse JSON response
            try:
                result = json.loads(response_text)
                
                # Enrich with actual line numbers from Neo4j data
                for item in result.get("affected_items", []):
                    # Find matching node from affected_nodes
                    for node in affected_nodes:
                        if (item.get("file") == node.get("file") and 
                            item.get("symbol") == node.get("symbol")):
                            # Use actual line number from Neo4j
                            item["line_number"] = node.get("line_number", item.get("line_number"))
                            item["symbol_type"] = node.get("symbol_type", item.get("symbol_type"))
                            break
                
                return result
                
            except json.JSONDecodeError as e:
                # Fallback: return structured error
                return {
                    "impact_level": "unknown",
                    "summary": f"Error parsing LLM response: {str(e)}",
                    "changed_file": filename,
                    "affected_items": [
                        {
                            "file": node.get("file"),
                            "symbol": node.get("symbol"),
                            "symbol_type": node.get("symbol_type", "unknown"),
                            "line_number": node.get("line_number"),
                            "depends_on": node.get("depends_on"),
                            "impact_reason": "Unable to analyze - LLM response parsing failed",
                            "breaking": False
                        }
                        for node in affected_nodes
                    ],
                    "recommendations": ["Manual review required due to analysis error"],
                    "error": f"JSON parsing failed: {str(e)}",
                    "raw_response": response_text[:500]
                }
                
        except Exception as e:
            # Fallback: return structured error
            return {
                "impact_level": "error",
                "summary": f"Error communicating with Groq API: {str(e)}",
                "changed_file": filename,
                "affected_items": [],
                "recommendations": ["Retry the analysis or check API connectivity"],
                "error": str(e)
            }
