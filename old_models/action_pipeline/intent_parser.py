import requests
import json
from typing import List, Dict

from config.api_keys import ANTHROPIC_API_KEY

class IntentParser:
    """Parses transcript chunks into actionable intents using Claude API"""
    
    API_URL = "https://api.anthropic.com/v1/messages"
    MODEL_NAME = "claude-3-opus-20240229"
    
    def __init__(self, api_key: str = ANTHROPIC_API_KEY):
        if not api_key or "your-anthropic-api-key" in api_key:
            raise ValueError("Anthropic API key not found. Please set it in config/api_keys.py or as an environment variable.")
        self.api_key = api_key
        
    def parse(self, text_chunks: List[str]) -> Dict:
        """Parse transcript chunks into structured intent"""
        combined_text = " ".join(text_chunks)
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        prompt = f"""
        Extract ONE actionable command from: "{combined_text}"
        
        Return valid JSON only, with no other text, comments, or explanations.
        The JSON object should have the following structure:
        {{
            "action": "schedule_meeting|add_reviewer|send_message|create_task|none",
            "entities": {{
                "person": "name if mentioned",
                "time": "when if mentioned", 
                "repo": "repository if mentioned",
                "channel": "channel if mentioned",
                "task_title": "task description if mentioned"
            }},
            "confidence": <a number between 0.0 and 1.0>,
            "ready": <true if all information for the action is present, otherwise false>,
            "description": "Human readable description of the action"
        }}
        """
        
        data = {
            "model": self.MODEL_NAME,
            "max_tokens": 1024,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(self.API_URL, headers=headers, json=data)
            response.raise_for_status()
            
            # The response from Claude is another JSON object.
            # We need to extract the text content.
            response_json = response.json()
            json_string = response_json.get("content", [{}])[0].get("text", "{}")
            
            # Parse the extracted JSON string
            return json.loads(json_string)
            
        except requests.exceptions.RequestException as e:
            print(f"Error calling Anthropic API: {e}")
            return {"action": "none", "error": str(e)}
        except json.JSONDecodeError:
            print(f"Error decoding JSON from Anthropic API response: {json_string}")
            return {"action": "none", "error": "Invalid JSON response from API"}
