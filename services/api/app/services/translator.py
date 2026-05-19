import json
import time
import re
from dataclasses import dataclass
from typing import List

@dataclass
class TranslationResult:
    source_text: str
    translated_text: str

def get_translation_prompt(source_texts, target_language):
    input_data = {str(i): text for i, text in enumerate(source_texts)}
    json_input = json.dumps(input_data, ensure_ascii=False, indent=2)
    
    return (
        f"You are a professional manga translator. Translate the following Japanese text blocks into natural {target_language}.\n"
        "INPUT FORMAT: A JSON object where keys are IDs and values are Japanese text.\n"
        "OUTPUT FORMAT: Return ONLY a JSON object with the exact same IDs, containing the translated text.\n"
        "Maintain character personalities, informal tone, and context between blocks.\n\n"
        f"INPUT JSON:\n{json_input}"
    )

def extract_json(content):
    # Some LLMs wrap JSON in markdown blocks
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        return json_match.group(0)
    return content.strip()

class GeminiTranslator:
    def __init__(self, api_key, model_name="models/gemini-2.0-flash"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Normalize model name
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
            
        self.model = genai.GenerativeModel(model_name)

    def translate_many(self, source_texts, target_language="English"):
        if not source_texts:
            return []

        prompt = get_translation_prompt(source_texts, target_language)

        from google.api_core import exceptions
        max_retries = 5
        base_delay = 2  # seconds
        
        for attempt in range(max_retries + 1):
            try:
                response = self.model.generate_content(prompt)
                content = response.text
                translated_dict = json.loads(extract_json(content))
                
                results = []
                for i in range(len(source_texts)):
                    translated_text = translated_dict.get(str(i), source_texts[i])
                    results.append(TranslationResult(source_texts[i], str(translated_text)))
                return results

            except (exceptions.ResourceExhausted, exceptions.ServiceUnavailable) as e:
                if attempt < max_retries:
                    wait_time = base_delay * (2 ** attempt)
                    print(f"!!! GEMINI RATE LIMIT (429/503). Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"!!! GEMINI ERROR: Quota exhausted after {max_retries} retries. {e}")
                    break
            except Exception as e:
                print(f"!!! GEMINI TRANSLATION ERROR: {e}")
                break

        return [TranslationResult(t, f"[Error: {t}]") for t in source_texts]

class OpenAITranslator:
    def __init__(self, api_key=None, model_name="gpt-4o", base_url=None):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key or "local", base_url=base_url)
        self.model = model_name

    def translate_many(self, source_texts, target_language="English"):
        if not source_texts:
            return []

        prompt = get_translation_prompt(source_texts, target_language)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"} if "llama" not in self.model.lower() else None
            )
            content = response.choices[0].message.content
            translated_dict = json.loads(extract_json(content))

            results = []
            for i in range(len(source_texts)):
                translated_text = translated_dict.get(str(i), source_texts[i])
                results.append(TranslationResult(source_texts[i], str(translated_text)))
            return results
        except Exception as e:
            print(f"!!! LLM TRANSLATION ERROR: {e}")
            return [TranslationResult(t, f"[Error: {t}]") for t in source_texts]

class ClaudeTranslator:
    def __init__(self, api_key, model_name="claude-3-5-sonnet-20240620"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model_name

    def translate_many(self, source_texts, target_language="English"):
        if not source_texts:
            return []

        prompt = get_translation_prompt(source_texts, target_language)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text
            translated_dict = json.loads(extract_json(content))

            results = []
            for i in range(len(source_texts)):
                translated_text = translated_dict.get(str(i), source_texts[i])
                results.append(TranslationResult(source_texts[i], str(translated_text)))
            return results
        except Exception as e:
            print(f"!!! CLAUDE TRANSLATION ERROR: {e}")
            return [TranslationResult(t, f"[Error: {t}]") for t in source_texts]

class GroqTranslator:
    def __init__(self, api_key, model_name="llama-3.3-70b-versatile"):
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model_name

    def translate_many(self, source_texts, target_language="English"):
        if not source_texts:
            return []

        prompt = get_translation_prompt(source_texts, target_language)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            translated_dict = json.loads(extract_json(content))

            results = []
            for i in range(len(source_texts)):
                translated_text = translated_dict.get(str(i), source_texts[i])
                results.append(TranslationResult(source_texts[i], str(translated_text)))
            return results
        except Exception as e:
            print(f"!!! GROQ TRANSLATION ERROR: {e}")
            return [TranslationResult(t, f"[Error: {t}]") for t in source_texts]

def get_translator(settings, provider=None, api_key=None, model_name=None, base_url=None):
    provider = provider or settings.llm_provider
    api_key = api_key or settings.llm_api_key
    model_name = model_name or settings.llm_model_name
    base_url = base_url or settings.llm_base_url

    if provider == "gemini":
        return GeminiTranslator(
            api_key=api_key,
            model_name=model_name or "models/gemini-2.0-flash"
        )
    elif provider == "openai":
        return OpenAITranslator(
            api_key=api_key,
            model_name=model_name or "gpt-4o",
            base_url=base_url
        )
    elif provider == "claude":
        return ClaudeTranslator(
            api_key=api_key,
            model_name=model_name or "claude-3-5-sonnet-20240620"
        )
    elif provider == "groq":
        return GroqTranslator(
            api_key=api_key,
            model_name=model_name or "llama-3.3-70b-versatile"
        )
    elif provider == "local":
        return OpenAITranslator(
            api_key=api_key or "ollama",
            model_name=model_name or "gemma2:9b",
            base_url=base_url or "http://localhost:11434/v1"
        )
    
    raise ValueError(f"No LLM provider configured or invalid provider: {provider}")
