from types import ModuleType
from collections.abc import Callable
from importlib import import_module

from .object import HistoryRequest, TickData, BarData
from .setting import SETTINGS
from .locale import _


class BaseDatafeed:
    """
    抽象数据服务类，用于连接不同的数据服务。
    """

    def init(self, output: Callable = print) -> bool:
        """
        初始化数据服务连接。
        """
        return False

    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> list[BarData]:
        """
        查询历史K线数据。
        """
        output(_("查询K线数据失败：没有正确配置数据服务"))
        return []

    def query_tick_history(self, req: HistoryRequest, output: Callable = print) -> list[TickData]:
        """
        查询历史Tick数据。
        """
        output(_("查询Tick数据失败：没有正确配置数据服务"))
        return []


datafeed: BaseDatafeed | None = None

def get_datafeed() -> BaseDatafeed:
    """"""
    # 如果已经初始化，则返回数据服务对象
    global datafeed
    if datafeed:
        return datafeed

    # 读取数据服务相关的全局配置
    datafeed_name: str = SETTINGS["datafeed.name"]

    if not datafeed_name:
        datafeed = BaseDatafeed()

        print(_("没有配置要使用的数据服务，请修改全局配置中的datafeed相关内容"))
    else:
        # 如果配置了 akshare，就返回 AkshareDatafeed
        if datafeed_name.lower() == "akshare":
            from vnpy.alpha.datafeed import AkshareDatafeed
            datafeed = AkshareDatafeed()
        else:
            module_name: str = f"vnpy_{datafeed_name}"
            try:
                module: ModuleType = import_module(module_name)
                datafeed = module.Datafeed()
            except ModuleNotFoundError:
                datafeed = BaseDatafeed()
                print(_("无法加载数据服务模块，请运行 pip install {} 尝试安装").format(module_name))

    return datafeed
