from collections.abc import AsyncIterator

from api_gateway.application.errors import (
    AnalysisServiceUnavailableError,
    DialogServiceUnavailableError,
    RetrievalServiceUnavailableError,
)
from api_gateway.application.ports import VersionProvider
from api_gateway.application.use_cases import (
    AnalyzeNewsUseCase,
    ChatStreamUseCase,
    ChatUseCase,
    IndexNewsUseCase,
    SearchNewsUseCase,
)
from api_gateway.presentation.errors import (
    map_analysis_error,
    map_dialog_error,
    map_retrieval_error,
)
from api_gateway.presentation.sse import format_sse_event, stream_error_event
from dishka.integrations.fastapi import FromDishka, inject
from economic_news_contracts.analysis import AnalyzeNewsRequest, AnalyzeNewsResponse
from economic_news_contracts.chat import ChatRequest, ChatResponse
from economic_news_contracts.retrieval import (
    IndexNewsRequest,
    IndexNewsResponse,
    SearchNewsRequest,
    SearchNewsResponse,
)
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/v1")


async def _chat_sse_stream(
    request: ChatRequest,
    use_case: ChatStreamUseCase,
) -> AsyncIterator[str]:
    try:
        async for event in use_case.stream(request):
            yield format_sse_event(event)
    except Exception as error:
        yield format_sse_event(stream_error_event(error))


@router.get("/version")
@inject
async def version(version_provider: FromDishka[VersionProvider]) -> dict[str, str]:
    return {"service": "api-gateway", "version": version_provider.get_version()}


@router.post("/analyze")
@inject
async def analyze(
    request: AnalyzeNewsRequest,
    use_case: FromDishka[AnalyzeNewsUseCase],
) -> AnalyzeNewsResponse:
    try:
        return await use_case.execute(request)
    except AnalysisServiceUnavailableError as error:
        raise map_analysis_error(error) from error


@router.post("/retrieval/index")
@inject
async def index_news(
    request: IndexNewsRequest,
    use_case: FromDishka[IndexNewsUseCase],
) -> IndexNewsResponse:
    try:
        return await use_case.execute(request)
    except RetrievalServiceUnavailableError as error:
        raise map_retrieval_error(error) from error


@router.post("/retrieval/search")
@inject
async def search_news(
    request: SearchNewsRequest,
    use_case: FromDishka[SearchNewsUseCase],
) -> SearchNewsResponse:
    try:
        return await use_case.execute(request)
    except RetrievalServiceUnavailableError as error:
        raise map_retrieval_error(error) from error


@router.post("/chat")
@inject
async def chat(
    request: ChatRequest,
    use_case: FromDishka[ChatUseCase],
) -> ChatResponse:
    try:
        return await use_case.execute(request)
    except AnalysisServiceUnavailableError as error:
        raise map_analysis_error(error) from error
    except RetrievalServiceUnavailableError as error:
        raise map_retrieval_error(error) from error
    except DialogServiceUnavailableError as error:
        raise map_dialog_error(error) from error


@router.post("/chat/stream")
@inject
async def chat_stream(
    request: ChatRequest,
    use_case: FromDishka[ChatStreamUseCase],
) -> StreamingResponse:
    return StreamingResponse(
        _chat_sse_stream(request, use_case),
        media_type="text/event-stream",
    )
