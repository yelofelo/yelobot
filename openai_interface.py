from openai import AsyncOpenAI
import dotenv

MODEL = 'ft:gpt-3.5-turbo-0613:personal::7qZhaoF6'

class OpenAIInterface:
    def __init__(self, api_key, model=MODEL):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(self, prompt, system_message, stop='\n\n', max_tokens=150, temperature=1.2):
        return await self.client.chat.completions.create(
            model=self.model,
            messages=[{'role': 'system', 'content': system_message}, {'role': 'user', 'content': prompt}],
            max_tokens=max_tokens,
            stop=stop,
            temperature=temperature
        ).choices[0].message['content'].strip()

if __name__ == '__main__':
    import os
    dotenv.load_dotenv()
    prompt = '''
YOU CAN ENTER A PROMPT HERE TO TEST LOCALLY
'''
    print(OpenAIInterface(os.getenv('OPENAI_API_KEY')).generate(prompt))
