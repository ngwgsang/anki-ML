import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
import streamlit as st
import typing_extensions as typing


# class Flashcard(typing.TypedDict):
#     word: str
#     meaning: str
#     example: str
    
class GeminiFlash:
    
    def __init__(self):
        self.generation_config = {
            "temperature": 1,
            "top_p": 0.5,
            "top_k": 25,
            "max_output_tokens": 1000,
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
    
    def run(self, prompt):
        genai.configure(api_key=st.session_state.GEMINI_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=self.generation_config,
        )
        response = model.generate_content(prompt, safety_settings=self.safe_settings)
        return response.text
    
    def run_json(self, prompt, response_schema=""):
        genai.configure(api_key=st.session_state.GEMINI_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.5,
                "top_p": 1,
                "top_k": 25,
                "max_output_tokens": 1000,
                "response_mime_type": "application/json",
                # "response_schema": response_schema
            },
        )
        response = model.generate_content(prompt, safety_settings=self.safe_settings)
        return response.text
    
    def extract_flashcard_action(self, plain_text, level):
        prompt = (
            "You are a helpful assistant designed to create concise and informative for Japanese language flashcards.\n"
            "N1: Advanced level, includes complex vocabulary often used in professional or academic contexts.\n"
            "N2: Upper-intermediate level, with vocabulary frequently used in business or media.\n"
            "N3: Intermediate level, covering vocabulary needed for daily life and workplace interactions.\n"
            "N4: Basic level, with words for everyday conversation and simple reading materials.\n"
            "N5: Beginner level, covering fundamental vocabulary for simple communication.\n"
            
            f"Generate some flashcard at level {level} from the TEXT i provided\n",
            f"\n\nTEXT: {plain_text}"
            "Rule 1: you will receive a word in Japanese and its meaning in Vietnamese.\n"
            "Rule 2: Response must be include keys: word, meaning, example.\n"
            
            "Use this JSON schema:\n"
            "Flashcard = {'word': str, 'meaning': str, 'example': str}\n"
            "Return: list[Flashcard]\n",
        )
        # new_flashcards = self.run_json(prompt, response_schema=list[Flashcard])
        new_flashcards = self.run_json(prompt)
        st.session_state['extracted_flashcards'] = json.loads(new_flashcards)
    
    def take_note_action(self):
        card = st.session_state.flashcards[st.session_state.index]
        prompt = (
            "Bạn là một trợ lý hữu ích, được thiết kế để tạo các ghi chú ngắn gọn và dễ hiểu cho flashcard học ngôn ngữ.\n"
            # "Với mỗi flashcard, bạn sẽ nhận được một từ và nghĩa của từ đó.\n"
            # "Nhiệm vụ của bạn là tạo một ghi chú ngắn giúp người dùng ghi nhớ từ và cách sử dụng từ đó trong ngữ cảnh thực tế.\n"
            # "Tập trung vào các ví dụ sử dụng từ trong thực tế để người học dễ dàng áp dụng.\n"
            # "Đảm bảo rằng các ghi chú của bạn rõ ràng, dễ hiểu, và viết bằng tiếng Việt.\n\n"
            # "Đối với cách đọc thì hãy dùng hiragana để thể hiện, không được sử dụng romanji hay Tiếng Việt.\n\n"
            "### THÔNG TIN HIỆN TẠI CỦA FLASHCARD\n"
            f"- **Từ:** {card['word']}\n"
            f"- **Nghĩa:** {card['meaning']}\n"
            f"- **Ví dụ:** {card['example']}\n\n"
            "### NHIỆM VỤ\n"
            f"- **Yêu cầu:** {st.session_state.new_note_content}\n"
            "Hãy tạo ghi chú ngắn gọn (không được lặp lại thông tin trên), và trình bày dưới dạng markdown bằng tiếng Việt."
            "Note ngắn gọn không ghi tiêu đề, chỉ ghi plain text hoặc bôi đen thôi"
        )
        # st.toast("prompt: " + prompt)
        return self.run(prompt) 
    