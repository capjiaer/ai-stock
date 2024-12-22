# Please install OpenAI SDK first: `pip3 install openai`
from openai import OpenAI
api_key = "sk-6a035a9bcdbb436a8164bd514e5c3283"
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "1+1"},
    ],
    stream=False,
    logprobs=True,
)


if __name__ == "__main__":
    info = response.choices[0].message.content
    info = response.choices[0].message
    print(type(info))
    print(info)