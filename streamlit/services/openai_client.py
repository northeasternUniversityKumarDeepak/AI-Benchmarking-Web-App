import openai

openai.api_key = '' # move this to a .env file

def get_model_answer(question):
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=question,
        max_tokens=100
    )
    return response.choices[0].text.strip()