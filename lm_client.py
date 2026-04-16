from openai import OpenAI
import config

def ask_lm_studio(prompt, system_prompt=None):
    """Отправляет запрос в LM Studio и возвращает ответ."""
    if system_prompt is None:
        system_prompt = "Ты — опытный аналитик проектов. Отвечай на русском, чётко, структурированно."

    client = OpenAI(
        base_url=config.LM_STUDIO_URL,
        api_key="not-needed"
    )
    try:
        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=config.LM_TEMPERATURE,
            max_tokens=config.LM_MAX_TOKENS
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Ошибка при обращении к LM Studio: {e}")
        return None