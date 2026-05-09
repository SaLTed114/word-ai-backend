import logging
import os
from typing import Any, Optional

import uvicorn
from dotenv import load_dotenv
from litestar import Litestar, get, post
from litestar.config.cors import CORSConfig
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- OpenAI Client ---
# Ensure API key is loaded
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("OPENAI_API_KEY environment variable not set.")
    # You might want to exit or raise a more specific configuration error
    # For now, we'll let it fail later if used.
else:
    logger.info("OpenAI API Key loaded.")

# Use Async Client
aclient = AsyncOpenAI(api_key=api_key)

# --- Pydantic Models (Structured Input/Output) ---


class BaseRequest(BaseModel):
    text: str = Field(..., description="The text to process.")
    context: Optional[str] = Field(None, description="Optional surrounding context.")


class GrammarCheckRequest(BaseRequest):
    pass


class CorrectionDetail(BaseModel):
    original_snippet: str
    corrected_snippet: str
    explanation: Optional[str] = None


class GrammarCheckResponse(BaseModel):
    original_text: str
    corrected_text: str
    corrections: list[CorrectionDetail] = Field(default_factory=list)
    success: bool = True
    message: Optional[str] = None


class WordSuggestRequest(BaseRequest):
    # Text here is likely the sentence/paragraph containing the word
    target_word: str = Field(
        ..., description="The specific word to get suggestions for."
    )


class WordSuggestion(BaseModel):
    suggestion: str
    reason: Optional[str] = None


class WordSuggestResponse(BaseModel):
    original_word: str
    suggestions: list[WordSuggestion] = Field(default_factory=list)
    success: bool = True
    message: Optional[str] = None


class StyleAdjustRequest(BaseRequest):
    target_style: str = Field(
        ...,
        description="Desired writing style (e.g., 'formal', 'concise', 'academic', 'informal').",
    )


class StyleAdjustResponse(BaseModel):
    original_text: str
    adjusted_text: str
    style_description: str
    changes_summary: Optional[str] = None
    success: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str


# --- Helper Function for OpenAI Calls ---


async def call_openai_api(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    """Generic helper to call OpenAI ChatCompletion API."""
    if not aclient.api_key:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI API key not configured on the server.",
        )
    try:
        logger.info(f"Sending prompt to OpenAI (model: {model}). Length: {len(prompt)}")
        response = await aclient.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert writing assistant. Provide concise and accurate responses based on the user's request.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,  # Adjust temperature as needed
        )
        result = response.choices[0].message.content
        logger.info(f"Received response from OpenAI. Length: {len(result or '')}")
        if not result:
            raise OpenAIError("Received empty response from OpenAI.")
        return result.strip()
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OpenAI API error: {e}"
        )
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during OpenAI call: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}",
        )


# --- API Endpoints ---


@post("/grammar-check", summary="Correct grammar and spelling mistakes.")
async def grammar_check(
    data: GrammarCheckRequest,
) -> GrammarCheckResponse | ErrorResponse:
    """
    Receives text and returns grammar/spelling corrections.
    Attempts to provide structured output via prompt engineering.
    """
    # Basic Prompt - Adapt as needed for better structured output
    # Note: Getting reliable JSON structure purely from prompts can be tricky.
    # Consider OpenAI function calling/tools for more robust JSON output if needed.
    prompt = f"""
    Please correct the grammar and spelling errors in the following text.
    Provide the fully corrected text.
    Also, try to identify key corrections made.

    Format your response STRICTLY as JSON with the following structure:
    {{
      "corrected_text": "The full corrected text here...",
      "corrections": [
        {{
          "original_snippet": "The original phrase with the error",
          "corrected_snippet": "The corrected phrase",
          "explanation": "Brief explanation (optional)"
        }}
      ]
    }}

    If no errors are found, return the original text in 'corrected_text' and an empty 'corrections' list.

    Text to check:
    ---
    {data.text}
    ---
    """
    try:
        response_str = await call_openai_api(prompt)
        # Attempt to parse the JSON response from OpenAI
        import json

        try:
            response_data = json.loads(response_str)
            # Validate required fields exist, even if empty
            corrected_text = response_data.get(
                "corrected_text", data.text
            )  # Default to original if missing
            corrections_data = response_data.get("corrections", [])

            # Ensure corrections have the right structure
            valid_corrections = []
            if isinstance(corrections_data, list):
                for item in corrections_data:
                    if (
                        isinstance(item, dict)
                        and "original_snippet" in item
                        and "corrected_snippet" in item
                    ):
                        valid_corrections.append(CorrectionDetail(**item))

            return GrammarCheckResponse(
                original_text=data.text,
                corrected_text=corrected_text,
                corrections=valid_corrections,
            )

        except json.JSONDecodeError:
            logger.warning(
                f"Failed to parse JSON response from OpenAI. Returning raw correction. Response: {response_str}"
            )
            # Fallback: return the raw response as the corrected text if JSON parsing fails
            return GrammarCheckResponse(
                original_text=data.text,
                corrected_text=response_str,  # Treat the whole response as corrected text
                corrections=[],
                message="AI response format unexpected, showing raw correction.",
            )

    except HTTPException as e:
        # Re-raise HTTP exceptions from call_openai_api
        return ErrorResponse(message=str(e.detail))
    except Exception as e:
        logger.error(f"Error in grammar_check endpoint: {e}", exc_info=True)
        return ErrorResponse(message=f"An internal server error occurred: {e}")


@post("/word-suggestion", summary="Suggest replacements for a specific word.")
async def word_suggestion(
    data: WordSuggestRequest,
) -> WordSuggestResponse | ErrorResponse:
    """
    Suggests alternative words for a target word within its context.
    """
    prompt = f"""
    Given the following text and a target word, suggest 3-5 alternative words or short phrases for '{data.target_word}'.
    Provide a brief reason for each suggestion based on the context.

    Format your response STRICTLY as JSON with the following structure:
    {{
      "suggestions": [
        {{
          "suggestion": "Alternative word/phrase",
          "reason": "Brief reason for this suggestion in context"
        }}
      ]
    }}

    Context Text:
    ---
    {data.text}
    ---
    Target Word: {data.target_word}
    """
    try:
        response_str = await call_openai_api(prompt)
        import json

        try:
            response_data = json.loads(response_str)
            suggestions_data = response_data.get("suggestions", [])

            valid_suggestions = []
            if isinstance(suggestions_data, list):
                for item in suggestions_data:
                    if isinstance(item, dict) and "suggestion" in item:
                        valid_suggestions.append(WordSuggestion(**item))

            return WordSuggestResponse(
                original_word=data.target_word, suggestions=valid_suggestions
            )
        except json.JSONDecodeError:
            logger.warning(
                f"Failed to parse JSON response for suggestions. Response: {response_str}"
            )
            return WordSuggestResponse(
                original_word=data.target_word,
                suggestions=[],
                message="AI response format unexpected, could not parse suggestions.",
            )

    except HTTPException as e:
        return ErrorResponse(message=str(e.detail))
    except Exception as e:
        logger.error(f"Error in word_suggestion endpoint: {e}", exc_info=True)
        return ErrorResponse(message=f"An internal server error occurred: {e}")


@post("/style-adjust", summary="Rewrite text to match a target style.")
async def style_adjust(data: StyleAdjustRequest) -> StyleAdjustResponse | ErrorResponse:
    """
    Rewrites the input text to conform to the specified target style.
    """
    prompt = f"""
    Rewrite the following text to adopt a '{data.target_style}' writing style.
    Maintain the core meaning of the original text.
    Provide a brief summary of the key changes made.

    Format your response STRICTLY as JSON with the following structure:
    {{
      "adjusted_text": "The rewritten text in the target style...",
      "changes_summary": "A brief summary of the style changes applied (e.g., 'Simplified sentence structure, used more formal vocabulary')."
    }}

    Original Text:
    ---
    {data.text}
    ---
    Target Style: {data.target_style}
    """
    try:
        response_str = await call_openai_api(prompt)
        import json

        try:
            response_data = json.loads(response_str)
            adjusted_text = response_data.get(
                "adjusted_text", f"Could not adjust style. Raw response: {response_str}"
            )
            changes_summary = response_data.get(
                "changes_summary", "No summary provided."
            )

            return StyleAdjustResponse(
                original_text=data.text,
                adjusted_text=adjusted_text,
                style_description=data.target_style,
                changes_summary=changes_summary,
            )
        except json.JSONDecodeError:
            logger.warning(
                f"Failed to parse JSON response for style adjustment. Response: {response_str}"
            )
            return StyleAdjustResponse(
                original_text=data.text,
                adjusted_text=response_str,  # Fallback to raw response
                style_description=data.target_style,
                changes_summary="AI response format unexpected.",
                message="AI response format unexpected, showing raw result.",
            )

    except HTTPException as e:
        return ErrorResponse(message=str(e.detail))
    except Exception as e:
        logger.error(f"Error in style_adjust endpoint: {e}", exc_info=True)
        return ErrorResponse(message=f"An internal server error occurred: {e}")


@get("/health", summary="Health check endpoint.")
async def health_check() -> dict[str, str]:
    """Simple health check."""
    logger.info("Health check requested.")
    return {"status": "ok"}


# --- CORS Configuration ---
# Allow requests from your Word Add-in's domain (or '*' for development, but be careful!)
# If running locally, Word Add-ins often run from localhost with a specific port.
cors_config = CORSConfig(
    allow_origins=["https://localhost:3000", "http://localhost:3000"]
)  # Adjust port if needed, or use '*' for local dev

# --- Create Litestar App ---
app = Litestar(
    route_handlers=[grammar_check, word_suggestion, style_adjust, health_check],
    cors_config=cors_config,
    # openapi_config=..., # Optional: customize OpenAPI docs
    debug=True,  # Set to False in production
)

# --- Run Server (for local development) ---
if __name__ == "__main__":
    # Use port 8000 for the backend API server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
