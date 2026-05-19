import json
from dataclasses import dataclass

@dataclass
class TranslationResult:
    source_text: str
    translated_text: str

class GeminiTranslator:
    def __init__(self, api_key, model_name="models/gemini-2.0-flash"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def translate_many(self, source_texts, target_language="English"):
        if not source_texts:
            return []

        # Create a dictionary for the LLM to translate
        # This helps keep the order correct
        input_data = {}
        for i, text in enumerate(source_texts):
            input_data[str(i)] = text
            
        json_input = json.dumps(input_data, ensure_ascii=False, indent=2)

        # Better, more professional prompt for higher accuracy
        prompt = (
            f"You are a professional manga translator. Translate the following Japanese text blocks into natural {target_language}.\n"
            "INPUT FORMAT: A JSON object where keys are IDs and values are Japanese text.\n"
            "OUTPUT FORMAT: Return ONLY a JSON object with the exact same IDs, containing the translated text.\n"
            "Maintain character personalities, informal tone, and context between blocks.\n\n"
            f"INPUT JSON:\n{json_input}"
        )

        try:
            response = self.model.generate_content(prompt)
            content = response.text
            
            # Use regex to find the JSON block if the LLM added conversational text
            import re
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                clean_json = json_match.group(0)
            else:
                clean_json = content.strip()

            translated_dict = json.loads(clean_json)
            
            results = []
            for i in range(len(source_texts)):
                translated_text = translated_dict.get(str(i), source_texts[i])
                results.append(TranslationResult(source_texts[i], str(translated_text)))
            return results
        except Exception as e:
            print(f"!!! GEMINI TRANSLATION ERROR: {e}")
            print(f"Raw Response was: {content if 'content' in locals() else 'No response'}")
            return [TranslationResult(t, f"[Error: {t}]") for t in source_texts]

class OpenAITranslator:
    def __init__(self, api_key=None, model_name="gpt-4o", base_url=None):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key or "local", base_url=base_url)
        self.model = model_name

    def translate_many(self, source_texts, target_language="English"):
        if not source_texts:
            return []

        input_data = {str(i): text for i, text in enumerate(source_texts)}
        json_input = json.dumps(input_data, ensure_ascii=False, indent=2)

        # Better, more professional prompt for higher accuracy
        prompt = (
            f"You are a professional manga translator. Translate the following Japanese text blocks into natural {target_language}.\n"
            "INPUT FORMAT: A JSON object where keys are IDs and values are Japanese text.\n"
            "OUTPUT FORMAT: Return ONLY a JSON object with the exact same IDs, containing the translated text.\n"
            "Maintain character personalities, informal tone, and context between blocks.\n\n"
            f"INPUT JSON:\n{json_input}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"} if "llama" not in self.model.lower() else None
            )
            content = response.choices[0].message.content
            
            # Use regex to find the JSON block
            import re
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                clean_json = json_match.group(0)
            else:
                clean_json = content.strip()

            translated_dict = json.loads(clean_json)

            results = []
            for i in range(len(source_texts)):
                translated_text = translated_dict.get(str(i), source_texts[i])
                results.append(TranslationResult(source_texts[i], str(translated_text)))
            return results
        except Exception as e:
            print(f"!!! LLM TRANSLATION ERROR: {e}")
            if 'content' in locals():
                print(f"Raw Response was: {content}")
            return [TranslationResult(t, f"[Error: {t}]") for t in source_texts]

def get_translator(settings, provider=None, api_key=None, model_name=None, base_url=None):
    """
    Factory function to pick the translator based on our settings or overrides
    """
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
    elif provider == "local":
        return OpenAITranslator(
            api_key=api_key or "ollama",
            model_name=model_name or "gemma2:9b",
            base_url=base_url or "http://localhost:11434/v1"
        )
    
    raise ValueError(f"No LLM provider configured or invalid provider: {provider}")
