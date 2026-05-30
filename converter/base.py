"""所有格式转换器的抽象基类。"""

import sys
from abc import ABC, abstractmethod
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


class Converter(ABC):
    """转换器基类，所有格式转换器都继承此类。

    子类必须实现 convert() 方法，接收输入文件路径和输出 HTML 路径。
    """

    def __init__(self):
        # 模板目录解析：exe 环境下从 exe 同目录 templates/ 读取（热修改实时生效），
        # 开发环境下从 converter/../templates/ 读取。
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后运行
            template_dir = Path(sys.executable).parent / "templates"
        else:
            # Python 源码运行
            template_dir = Path(__file__).resolve().parent.parent / "templates"
        self._jinja = Environment(loader=FileSystemLoader(str(template_dir)))

    @abstractmethod
    def convert(self, input_path: Path, output_path: Path) -> None:
        """将 input_path 指向的源文件转换为 HTML，写入 output_path。"""
        ...

    @property
    def output_path(self) -> Path:
        """当前转换的输出路径（子类应在 convert() 开头设置）。"""
        if not hasattr(self, '_output_path'):
            raise RuntimeError("output_path not set — set self._output_path in convert()")
        return self._output_path

    def render_template(self, template_name: str, **kwargs) -> str:
        """从 templates/ 目录加载 Jinja2 模板并渲染为字符串。

        参数：
            template_name: 模板文件名（如 'base.html'）
            **kwargs: 传入模板的变量
        返回：
            渲染后的完整 HTML 字符串
        """
        template = self._jinja.get_template(template_name)
        return template.render(**kwargs)
