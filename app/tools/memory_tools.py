from langchain.tools import tool, ToolRuntime
from app.core.state import TravelState
from app.core.store import get_user_memory_service
from app.utils.logger import app_logger


# ============== 1️⃣ 读取用户记忆工具 ==============

@tool
async def get_user_memory_tool(
        runtime: ToolRuntime[None, TravelState] = None
) -> str:
    """
    获取用户的长期记忆信息。

    在以下场景调用此工具：
    - 需要了解用户历史偏好时
    - 开始新的规划流程时
    - 用户询问"你还记得我喜欢什么吗"时

    返回：
    - 用户的旅行风格、饮食偏好、出行历史等信息
    """
    user_id = runtime.state.get("user_id")

    if not user_id:
        return "未识别到用户身份，无法获取历史记忆"

    try:
        service = await get_user_memory_service()
        memory_text = await service.format_memory_for_prompt(user_id)

        if memory_text:
            app_logger.info(f"读取用户记忆: {user_id}")
            return memory_text
        else:
            return "暂无历史偏好记录，这是您的首次使用"

    except Exception as e:
        app_logger.error(f"❌ 读取用户记忆失败: {e}")
        return f"❌ 读取记忆时出错: {str(e)}"


# ============== 2️⃣ 更新旅行风格偏好工具 ==============

@tool
async def update_travel_style_tool(
        styles: list[str],
        runtime: ToolRuntime[None, TravelState] = None
) -> str:
    """
    记录或更新用户的旅行风格偏好。

    当用户表达以下类型的偏好时调用此工具：
    - "我喜欢休闲度假" → ["休闲度假"]
    - "我喜欢体验文化" → ["文化探索"]
    - "我喜欢刺激的户外活动" → ["户外冒险"]
    - "我是个吃货，主要为了美食" → ["美食之旅"]
    - "我喜欢文化和美食" → ["文化探索", "美食之旅"]

    参数说明：
    - styles: 喜欢的旅行风格列表，举例(可以是其他旅行风格)：
      * 休闲度假（放松、度假、休息）
      * 文化探索（历史、博物馆、古迹）
      * 户外冒险（徒步、攀岩、极限运动）
      * 美食之旅（吃货、美食、小吃）
    """
    user_id = runtime.state.get("user_id")

    if not user_id:
        return "⚠️ 未识别到用户身份，无法保存偏好"

    try:
        service = await get_user_memory_service()
        await service.update_travel_styles(user_id, styles)

        app_logger.info(f"💾 保存旅行风格: {user_id} -> {styles}")
        return f"✅ 已记录您的旅行风格偏好：{', '.join(styles)}"

    except Exception as e:
        app_logger.error(f"❌ 保存旅行风格失败: {e}")
        return f"⚠️ 保存失败: {str(e)}"


# ============== 3️⃣ 更新饮食禁忌工具 ==============

@tool
async def update_dietary_restriction_tool(
        restrictions: list[str],
        runtime: ToolRuntime[None, TravelState] = None
) -> str:
    """
    记录或更新用户的饮食禁忌/过敏信息。

    当用户提到以下信息时调用此工具：
    - "我是素食主义者" → ["只吃素食"]
    - "我对海鲜过敏" → ["海鲜过敏"]
    - "我不能吃含麸质的食物" → ["无麸质"]
    - "我对花生过敏" → ["花生过敏"]
    - "我不爱吃牛肉" → ["不爱吃牛肉"]
    - "我乳糖不耐受" → ["乳糖不耐受"]

    参数说明：
    - restrictions: 饮食禁忌列表，参数举例(可以是其他饮食禁忌)：
      * 无麸质（麸质过敏）
      * 海鲜过敏
      * 花生过敏
      * 乳糖不耐受
      * 不吃牛肉
      * 不吃猪肉
      * 不吃羊肉
      * 鸡蛋过敏

    注意：这些信息对用户健康很重要，务必准确记录！
    """
    user_id = runtime.state.get("user_id")

    if not user_id:
        return "⚠️ 未识别到用户身份，无法保存饮食禁忌"

    try:
        service = await get_user_memory_service()
        await service.update_dietary_restrictions(user_id, restrictions)

        app_logger.info(f"💾 保存饮食禁忌: {user_id} -> {restrictions}")
        return f"✅ 已记录您的饮食禁忌：{', '.join(restrictions)}。后续推荐会特别注意避开这些食物。"

    except Exception as e:
        app_logger.error(f"❌ 保存饮食禁忌失败: {e}")
        return f"⚠️ 保存失败: {str(e)}"


# ============== 4️⃣ 更新饮食偏好工具 ==============

@tool
async def update_food_preference_tool(
        preferences: list[str],
        runtime: ToolRuntime[None, TravelState] = None
) -> str:
    """
    记录或更新用户的饮食偏好（喜欢吃什么）。

    当用户表达饮食喜好时调用此工具：
    - "我喜欢吃辣" → ["辣"]
    - "我喜欢甜食" → ["甜"]
    - "我喜欢尝试当地特色美食" → ["当地特色"]
    - "我喜欢吃烧烤" → ["烧烤"]
    - "我喜欢海鲜" → ["海鲜"]
    - "我偏好清淡口味" → ["清淡"]

    参数说明：
    - preferences: 饮食偏好列表，参数举例(可以是其他饮食偏好)：
      * 辣
      * 甜
      * 酸
      * 清淡
      * 重口味
      * 当地特色
      * 海鲜
      * 烧烤
      * 火锅
      * 面食
      * 米饭
      * 小吃
      * 西餐
      * 日料
      * 韩餐
    """
    user_id = runtime.state.get("user_id")

    if not user_id:
        return "⚠️ 未识别到用户身份，无法保存饮食偏好"

    try:
        service = await get_user_memory_service()
        await service.update_food_preferences(user_id, preferences)

        app_logger.info(f"💾 保存饮食偏好: {user_id} -> {preferences}")
        return f"✅ 已记录您的饮食偏好：{', '.join(preferences)}"

    except Exception as e:
        app_logger.error(f"❌ 保存饮食偏好失败: {e}")
        return f"⚠️ 保存失败: {str(e)}"


# ============== 5️⃣ 更新住宿偏好工具 ==============

@tool
async def update_accommodation_preference_tool(
        preferred_types: list[str] = None,
        avg_budget_per_night: float = None,
        runtime: ToolRuntime[None, TravelState] = None
) -> str:
    """
    记录或更新用户的住宿偏好。

    当用户表达住宿喜好时调用此工具：
    - "我喜欢住有特色的民宿" → preferred_types=["有特色的民宿"]
    - "我习惯住五星级酒店" → preferred_types=["星级酒店"]
    - "住宿预算大概300一晚" → avg_budget_per_night=300
    - "我喜欢经济实惠的酒店，200左右就行" → preferred_types=["经济实惠的酒店"], avg_budget_per_night=200

    参数说明：
    - preferred_types: 偏好的住宿类型列表，参数举例(可以是其他偏好的住宿类型)：
      * 星级酒店（四星、五星级酒店）
      * 经济酒店（快捷酒店、连锁酒店）
      * 特色民宿（有特色的民宿、客栈）
      * 青年旅社（背包客、青旅）
    - avg_budget_per_night: 平均每晚预算（元），可选
    """
    user_id = runtime.state.get("user_id")

    if not user_id:
        return "⚠️ 未识别到用户身份，无法保存住宿偏好"

    if not preferred_types and not avg_budget_per_night:
        return "⚠️ 请至少提供住宿类型或预算信息"

    try:
        service = await get_user_memory_service()
        await service.update_accommodation_preference(
            user_id=user_id,
            preferred_types=preferred_types,
            avg_budget=avg_budget_per_night
        )

        result_parts = ["✅ 已记录您的住宿偏好："]

        if preferred_types:
            result_parts.append(f"类型偏好 - {', '.join(preferred_types)}")

        if avg_budget_per_night:
            result_parts.append(f"预算 - 约 {avg_budget_per_night:.0f} 元/晚")

        app_logger.info(f"保存住宿偏好: {user_id}")
        return "；".join(result_parts)

    except Exception as e:
        app_logger.error(f"❌ 保存住宿偏好失败: {e}")
        return f"⚠️ 保存失败: {str(e)}"


# ============== 6️⃣ 添加出行历史工具 ==============

@tool
async def add_travel_record_tool(
        destination: str,
        visited_attractions: list[str] = None,
        start_date: str = None,
        end_date: str = None,
        runtime: ToolRuntime[None, TravelState] = None
) -> str:
    """
    记录用户的历史出行记录。

    当用户提到过去的旅行经历时调用此工具：
    - "我去年去过西安" → destination="西安"
    - "我之前去过故宫和长城" → destination="北京", visited_attractions=["故宫", "长城"]
    - "上个月刚去了成都，玩了大熊猫基地" → destination="成都", visited_attractions=["大熊猫基地"]

    参数说明：
    - destination: 目的地名称（必填）
    - visited_attractions: 去过的景点列表（可选）
    - start_date: 出发日期 YYYY-MM-DD（可选）
    - end_date: 结束日期 YYYY-MM-DD（可选）

    记录出行历史的好处：
    - 避免重复推荐去过的地方
    - 了解用户的旅行经验水平
    - 提供更个性化的推荐
    """
    user_id = runtime.state.get("user_id")

    if not user_id:
        return "⚠️ 未识别到用户身份，无法保存出行历史"

    if not destination:
        return "⚠️ 请提供目的地名称"

    try:
        service = await get_user_memory_service()
        await service.add_completed_trip(
            user_id=user_id,
            destination=destination,
            start_date=start_date or "",
            end_date=end_date or "",
            visited_attractions=visited_attractions or []
        )

        result = f"✅ 已记录您去过 {destination}"
        if visited_attractions:
            result += f"，游玩了：{', '.join(visited_attractions)}"
        result += "。后续推荐会避免重复这些地方。"

        app_logger.info(f"💾 保存出行历史: {user_id} -> {destination}")
        return result

    except Exception as e:
        app_logger.error(f"❌ 保存出行历史失败: {e}")
        return f"⚠️ 保存失败: {str(e)}"


# ============== 工具导出 ==============

MEMORY_TOOLS = [
    update_travel_style_tool,
    update_dietary_restriction_tool,
    update_food_preference_tool,
    update_accommodation_preference_tool,
    add_travel_record_tool,
]