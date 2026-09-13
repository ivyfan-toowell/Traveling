"""
交通规划专用状态扩展
"""
from typing import TypedDict, Annotated, Optional, Literal
from typing_extensions import NotRequired
from operator import add

# ============== 交通类型定义 ==============

TransportType = Literal["flight", "train", "driving"]


# ============== 航班信息结构 ==============

class FlightOption(TypedDict):
    """单个航班选项"""
    flight_number: str  # 航班号
    airline: str  # 航空公司
    departure_airport: str  # 出发机场
    arrival_airport: str  # 到达机场
    departure_time: str  # 起飞时间
    arrival_time: str  # 降落时间
    duration: str  # 飞行时长
    price: float  # 价格
    cabin_class: str  # 舱位等级
    available_seats: int  # 剩余座位


# ============== 高铁信息结构 ==============

class TrainOption(TypedDict):
    """单个车次选项"""
    train_number: str  # 车次号
    departure_station: str  # 出发站
    arrival_station: str  # 到达站
    departure_time: str  # 发车时间
    arrival_time: str  # 到站时间
    duration: str  # 运行时长
    seat_types: list[str]  # 可选座位类型
    prices: dict[str, float]  # 各座位类型价格
    available: bool  # 是否有票


# ============== 自驾信息结构 ==============

class DrivingRoute(TypedDict):
    """自驾路线"""
    route_name: str  # 路线名称（推荐路线/最短路线）
    distance: str  # 总距离
    duration: str  # 预计时长
    toll_fee: float  # 过路费
    fuel_cost: float  # 油费估算
    steps: list[str]  # 导航步骤
    waypoints: list[str]  # 途经城市


# ============== 交通规划状态扩展 ==============

class TransportState(TypedDict):
    """交通规划专用状态"""

    # 用户选择
    selected_transport: NotRequired[TransportType]

    # 查询参数
    origin_city: NotRequired[str]  # 出发城市
    destination_city: NotRequired[str]  # 目的地城市
    departure_date: NotRequired[str]  # 出发日期
    passenger_count: NotRequired[int]  # 乘客数量

    # 查询结果（累加）
    flight_options: Annotated[list[FlightOption], add]
    train_options: Annotated[list[TrainOption], add]
    driving_routes: Annotated[list[DrivingRoute], add]

    # 最终选择
    selected_flight: NotRequired[FlightOption]
    selected_train: NotRequired[TrainOption]
    selected_route: NotRequired[DrivingRoute]