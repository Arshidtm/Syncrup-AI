import os
from groq import Groq
import json

class GroqAnalyzer:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def analyze_impact(self, filename: str, affected_nodes: list, changes: str = "", code_context: str = ""):
        """
        Uses Groq (LLaMA-3) to perform a "Reasoned Impact Analysis".
        It compares the specific change to the dependency list and decides if a break is likely.
        """
        if not affected_nodes:
            return f"The knowledge graph shows no downstream dependencies for {filename}. This change is isolated."

        prompt = f"""
        ACT AS: A Senior Software Architect performing a Code Impact Review.
        
        GOAL: Determine if the specific code changes in '{filename}' will ACTUALLY BREAK the downstream symbols listed below.
        
        CHANGE DESCRIPTION PROVIDED BY DEVELOPER:
        "{changes if changes else "The developer did not provide a description, assume generic logic changes."}"
        
        ACTUAL CODE CONTEXT (IF AVAILABLE):
        {code_context if code_context else "No code snippet provided."}
        
        DEPENDENCY LIST FROM KNOWLEDGE GRAPH (The "Blast Zone"):
        {json.dumps(affected_nodes, indent=2)}
        
        CRITICAL INSTRUCTIONS:
        1. VALIDATE IMPACT: Does the change described (e.g., renaming a function, changing a parameter) actually affect how the symbols in the "Blast Zone" call this file?
        2. NO IMPACT CASE: If the change is purely internal (like changing a print statement, adding a comment, or fixing a bug inside a function body without changing its name/signature), state clearly: "NO BREAKING IMPACT DETECTED".
        3. BE SPECIFIC: If it breaks, name the exact function and the reason (e.g. 'TypeError: parameter mismatch').
        4. BREVITY: Do not give generic advice. If there is no impact, stop after saying so.

        RESPONSE FORMAT:
        - Impact Assessment: [High / Internal Only / No Impact]
        - Reasoning: [1-2 sentences explaining why it breaks or why it is safe]
        - Affected Symbols: [List and File] (ONLY if Impact is High)
        """

        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, # Low temperature for factual reasoning
                max_tokens=500
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error communicating with Groq: {str(e)}"
