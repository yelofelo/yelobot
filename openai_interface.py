import openai
import dotenv

MODEL = 'babbage:ft-personal:yelobot-babbage-apr22-curated-2022-05-30-05-33-57'

class OpenAIInterface:
    def __init__(self, api_key, model=MODEL):
        openai.api_key = api_key
        self.model = model

    def generate(self, prompt, stop='\n\n', max_tokens=150, temperature=0.55):
        return openai.Completion.create(
            model=self.model,
            prompt=prompt,
            max_tokens=max_tokens,
            stop=stop,
            temperature=temperature
        )['choices'][0]['text'].strip()

if __name__ == '__main__':
    import os
    dotenv.load_dotenv()
    prompt = '''
YOU CAN ENTER A PROMPT HERE TO TEST LOCALLY
'''
    print(OpenAIInterface(os.getenv('OPENAI_API_KEY')).generate(prompt))
