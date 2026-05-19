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
            # Remove any markdown code blocks if the LLM added them
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            translated_dict = json.loads(clean_json)
            
            results = []
            for i in range(len(source_texts)):
                translated_text = translated_dict.get(str(i), source_texts[i])
                results.append(TranslationResult(source_texts[i], str(translated_text)))
            return results
        except Exception as e:
            print(f"Error during Gemini translation: {e}")
            return [TranslationResult(t, t) for t in source_texts]

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
            clean_json = content.replace("```json", "").replace("```", "").strip()
            translated_dict = json.loads(clean_json)

            results = []
            for i in range(len(source_texts)):
                translated_text = translated_dict.get(str(i), source_texts[i])
                results.append(TranslationResult(source_texts[i], str(translated_text)))
            return results
        except Exception as e:
            print(f"Error during LLM translation: {e}")
            return [TranslationResult(t, t) for t in source_texts]

def get_translator(settings):
    """
    Factory function to pick the translator based on our settings
    """
    if settings.llm_provider == "gemini":
        return GeminiTranslator(
            api_key=settings.llm_api_key,
            model_name=settings.llm_model_name or "models/gemini-2.0-flash"
        )
    elif settings.llm_provider == "openai":
        return OpenAITranslator(
            api_key=settings.llm_api_key,
            model_name=settings.llm_model_name or "gpt-4o",
            base_url=settings.llm_base_url
        )
    elif settings.llm_provider == "local":
        return OpenAITranslator(
            api_key="ollama",
            model_name=settings.llm_model_name or "llama3",
            base_url=settings.llm_base_url or "http://localhost:11434/v1"
        )
    
    raise ValueError("No LLM provider configured! Check your .env file.")
