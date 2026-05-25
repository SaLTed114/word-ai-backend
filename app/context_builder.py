from __future__ import annotations

from app.models import ContextBuildResult, DocumentContextRequest, TextContext, TextRequest


def build_text_request_from_document(request: DocumentContextRequest) -> ContextBuildResult:
    document_text = request.document_text or ""
    warnings: list[str] = []

    start, end, selected_text = _resolve_selection(request, document_text, warnings)
    active_scope = request.active_scope

    if active_scope == "document":
        selected_text = document_text or selected_text
        start = 0 if document_text else None
        end = len(document_text) if document_text else None
    elif active_scope == "paragraph" and document_text:
        start, end, selected_text = _expand_to_paragraph(document_text, start, end)
    elif active_scope == "section":
        warnings.append("Section scope is not implemented yet; using the current selection.")

    if not selected_text:
        raise ValueError("No selected text or document text was provided.")

    before, after = _slice_context(
        document_text=document_text,
        start=start,
        end=end,
        window=request.context_window_chars,
    )

    text_request = TextRequest(
        text=selected_text,
        context=TextContext(
            before=before,
            after=after,
            document_title=request.title,
            section_heading=request.section_heading,
            document_id=request.document_id,
            active_scope=active_scope,
        ),
        instruction=request.instruction,
        style=request.style,
    )
    return ContextBuildResult(
        text_request=text_request,
        active_scope=active_scope,
        selected_text=selected_text,
        before_chars=len(before or ""),
        after_chars=len(after or ""),
        warnings=warnings,
    )


def _resolve_selection(
    request: DocumentContextRequest,
    document_text: str,
    warnings: list[str],
) -> tuple[int | None, int | None, str]:
    selection = request.selection
    if selection is None:
        if document_text:
            warnings.append("No selection was provided; using the full document text.")
            return 0, len(document_text), document_text
        return None, None, ""

    start = selection.start
    end = selection.end
    selected_text = selection.text or ""

    if document_text and start is not None and end is not None:
        if start > end:
            raise ValueError("selection.start must be less than or equal to selection.end.")
        if end > len(document_text):
            raise ValueError("selection.end is outside document_text.")
        sliced_text = document_text[start:end]
        if selected_text and selected_text != sliced_text:
            warnings.append("selection.text does not match document_text[start:end]; using offsets.")
        return start, end, sliced_text

    if document_text and selected_text:
        start = document_text.find(selected_text)
        if start >= 0:
            end = start + len(selected_text)
            if document_text.find(selected_text, end) >= 0:
                warnings.append("Selected text appears multiple times; using the first occurrence.")
            return start, end, selected_text
        warnings.append("selection.text was not found in document_text; context windows are unavailable.")

    if selected_text:
        return start, end, selected_text

    if document_text:
        warnings.append("Empty selection was provided; using the full document text.")
        return 0, len(document_text), document_text

    return None, None, ""


def _expand_to_paragraph(
    document_text: str,
    start: int | None,
    end: int | None,
) -> tuple[int, int, str]:
    if start is None:
        start = 0
    if end is None:
        end = start

    para_start = document_text.rfind("\n\n", 0, start)
    para_start = 0 if para_start < 0 else para_start + 2

    para_end = document_text.find("\n\n", end)
    para_end = len(document_text) if para_end < 0 else para_end

    return para_start, para_end, document_text[para_start:para_end]


def _slice_context(
    document_text: str,
    start: int | None,
    end: int | None,
    window: int,
) -> tuple[str | None, str | None]:
    if not document_text or start is None or end is None:
        return None, None

    before_start = max(0, start - window)
    after_end = min(len(document_text), end + window)
    return document_text[before_start:start], document_text[end:after_end]
