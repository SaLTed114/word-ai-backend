import uvicorn
from litestar import Litestar, Response, post
from litestar.config.cors import CORSConfig
from litestar.di import Provide
from openai.types.chat import ParsedChatCompletion
from ai import (
    AIClient,
    AIConfigManager,
    format_style_prompt,
    format_syntax_prompt,
    format_word_prompt,
)
from model import (
    AIConfig,
    CorrectionResponse,
    StyleAdjustmentRequest,
    StyleAdjustmentResponse,
    SyntaxCheckRequest,
    WordCheckRequest,
)

ai_config_manager = AIConfigManager()


async def get_ai_client(config_manager: AIConfigManager) -> AIClient:
    return await ai_config_manager.get_client()


dependencies = {
    "config_manager": Provide(
        lambda: ai_config_manager, sync_to_thread=False, use_cache=True
    ),
    "ai_client": Provide(
        get_ai_client,
        sync_to_thread=False,
        use_cache=False,
    ),
}


@post("/config/ai")
async def update_ai_config(
    data: AIConfig, config_manager: AIConfigManager  # Inject the manager
) -> Response:
    print(f"Received request to update API key to: {data.api_key}")
    await config_manager.update(data.api_key, data.model, data.base_url)
    return Response(
        {
            "message": "AI configuration updated successfully.",
            "new_config_info": config_manager.get_current_config_info(),
        },
    )


@post("/syntax")
async def syntax_check(
    data: SyntaxCheckRequest,
    ai_client: AIClient,  # Inject the AI client
) -> CorrectionResponse:
    response: ParsedChatCompletion[CorrectionResponse] = (
        await ai_client.generate_response_format(
            format_syntax_prompt(data.text),
            CorrectionResponse,
        )
    )
    print(response)
    return response.choices[0].message.parsed


@post("/word")
async def word_check(
    data: WordCheckRequest,
    ai_client: AIClient,  # Inject the AI client
) -> CorrectionResponse:
    response: ParsedChatCompletion[CorrectionResponse] = (
        await ai_client.generate_response_format(
            format_word_prompt(data.text),
            CorrectionResponse,
        )
    )
    print(response)
    return response.choices[0].message.parsed


@post("/style")
async def style_adjust(
    data: StyleAdjustmentRequest,
    ai_client: AIClient,  # Inject the AI client
) -> StyleAdjustmentResponse:
    response: ParsedChatCompletion[StyleAdjustmentResponse] = (
        await ai_client.generate_response_format(
            format_style_prompt(data.target_style, data.text),
            StyleAdjustmentResponse,
        )
    )
    print(response)
    return response.choices[0].message.parsed


app = Litestar(
    route_handlers=[update_ai_config, syntax_check, word_check, style_adjust],
    dependencies=dependencies,
    debug=True,
    cors_config=CORSConfig(
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,
    ),
)


if __name__ == "__main__":
    uvicorn.run(
        app,
        ssl_certfile="C:\\Users\\SaLTed\\.office-addin-dev-certs\\localhost.crt",
        ssl_keyfile="C:\\Users\\SaLTed\\.office-addin-dev-certs\\localhost.key",
    )
