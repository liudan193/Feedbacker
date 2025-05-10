from openai import OpenAI

# init client and connect to localhost server
client = OpenAI(
    base_url="http://0.0.0.0:8006",  # change the default port if needed
    api_key="fake-api-key",
)

# call API
chat_completion = client.chat.completions.create(
    messages=[{
        "role": "user",
        "content": "Who are you?",
    }],
    model="gpt-4o"
)

print(chat_completion)

# print the top "choice"
print(chat_completion.choices[0].message.content)