from app.core.config import settings


def generate_output(prompt: str) -> str:
    """
    Generate an LLM response for the given prompt.

    Uses OpenAI gpt-3.5-turbo when OPENAI_API_KEY is set in .env.
    Falls back to a deterministic mock response so the pipeline works
    without any API key — useful for local development and demos.
    """
    if settings.OPENAI_API_KEY:
        # Real path: calls the OpenAI Chat Completions API
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    # Mock path: no API call, instant response — good for understanding the flow
    return f"AI response to: {prompt}"
