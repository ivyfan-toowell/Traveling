"""
天气服务 MCP Server
使用高德天气 API 查询天气预报
"""
import os
import json
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("weather-service")

AMAP_API_KEY = os.getenv("AMAP_API_KEY")
AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"


@mcp.tool()
async def get_weather_forecast(city_adcode: str) -> str:
    """
    查询城市未来天气预报

    Args:
        city_adcode: 城市/区域的 adcode 编码 (例如: 北京="110000", 上海="310000",
                     西安="610100", 成都="510100", 深圳="440300", 杭州="330100",
                     广州="440100", 南京="320100", 重庆="500000", 武汉="420100")。
                     注意：API 不支持直接使用中文城市名，必须使用 adcode。

    Returns:
        JSON 格式的未来天气预报数据 (包含白天/晚上的天气、温度、风力等)。
    """

    if not AMAP_API_KEY:
        return json.dumps({"error": "未配置 AMAP_API_KEY"}, ensure_ascii=False)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # async with .... 开启异步池
        try:
            # client.get：向 API 发送指令
            response = await client.get(
                AMAP_WEATHER_URL,
                params={
                    "key": AMAP_API_KEY,
                    "city": city_adcode,
                    "extensions": "all",  # all 代表我们要查询“预报天气”
                    "output": "JSON"
                }
            )
            response.raise_for_status()

            data = response.json()  # 将返回的字符串转成 Python 字典

            if data.get("status") != "1":  # 高德 API 约定 status="1" 才是成功
                return json.dumps({
                    "error": data.get("info", "查询失败"),
                    "infocode": data.get("infocode")
                }, ensure_ascii=False)

            # ... 后面是提取具体的 city, province, casts (天气列表)
            forecasts = data.get("forecasts", [])
            if not forecasts:
                return json.dumps({"error": "未找到天气数据"}, ensure_ascii=False)

            forecast = forecasts[0]  # 提取第一个城市的天气对象

            result = {
                "city": forecast.get("city"),
                "adcode": forecast.get("adcode"),
                "province": forecast.get("province"),
                "reporttime": forecast.get("reporttime"),
                "casts": forecast.get("casts", [])  # 从第一个城市结果里拿未来几天的天气数组
            }

            # indent=2代表每一层缩进 2 个空格
            return json.dumps(result, ensure_ascii=False, indent=2)

        except httpx.TimeoutException:
            return json.dumps({"error": "请求超时"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
