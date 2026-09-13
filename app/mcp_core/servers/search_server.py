"""
搜索服务 MCP Server
使用 Tavily API 搜索旅游相关信息
"""
import os
import json
from dotenv import load_dotenv
import httpx
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("search-service")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_URL = "https://api.tavily.com/search"


@mcp.tool()
async def search_travel_info(query: str, max_results: int = 5) -> str:
    """
    搜索旅游相关信息（景点、攻略、美食、住宿等）

    Args:
        query: 搜索关键词，如 "西安旅游攻略"、"西安必去景点"、"西安美食推荐"、
               "成都住宿推荐"、"北京交通指南" 等
        max_results: 返回结果数量，默认5条，最多10条

    Returns:
        JSON 格式的搜索结果，包含 answer(摘要) 和 results(详细结果列表)
    """

    if not TAVILY_API_KEY:
        return json.dumps({"error": "未配置 TAVILY_API_KEY"}, ensure_ascii=False)

    max_results = min(max_results, 10)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                TAVILY_URL,
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                    "include_answer": True,
                }
            )
            # client.post：与天气服务的 GET 不同，Tavily 要求使用 POST 请求，并将参数放在 json 体中发送。
            # search_depth="basic"：Tavily 提供 basic 和 advanced 两种深度，基础搜索速度更快。
            # include_answer=True：这是 Tavily 的特色，它会直接给出一个针对问题的摘要回答，而不仅仅是网页链接。

            if response.status_code != 200:
                return json.dumps({
                    "error": f"API 请求失败: {response.status_code}"
                }, ensure_ascii=False)

            data = response.json()  # 转回python字典

            result = {
                "query": query,
                "answer": data.get("answer"),
                "results": [
                    {
                        "title": r.get("title"),
                        "url": r.get("url"),
                        "content": r.get("content", "")[:300]  # 截断处理
                    }
                    for r in data.get("results", [])
                ]
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except httpx.TimeoutException:
            return json.dumps({"error": "请求超时"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")