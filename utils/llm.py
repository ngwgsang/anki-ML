import google.generativeai as genai

class GeminiFlask:
    
    def __init__(self):
        self.generation_config = {
            "temperature": 1,
            "top_p": 0.75,
            "top_k": 1,
            "max_output_tokens": 256,
            "response_mime_type": "text/plain",
        }
        self.safe_settings = [
            {
                "category": "HARM_CATEGORY_DANGEROUS",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
            },
        ]
    
    def run(self, prompt, key):
        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=self.generation_config,
        )
        response = model.generate_content(prompt, safety_settings=self.safe_settings)
        return response.text
    
    def run_json(self, prompt, key):
        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 1,
                "top_p": 0.75,
                "top_k": 1,
                "max_output_tokens": 512,
                "response_mime_type": "application/json", 
            },
        )
        response = model.generate_content(prompt, safety_settings=self.safe_settings)
        return response.text