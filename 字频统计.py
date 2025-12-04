#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author: 虎码新手2群-也无风雨也无晴

# 工具版本号
TOOL_VERSION = "1.3"

import os
import sys
import io
import unicodedata
from collections import Counter

# 尝试导入数据库上传模块（可选功能）
try:
    from db_uploader import handle_database_upload
    DB_UPLOAD_AVAILABLE = True
except ImportError:
    DB_UPLOAD_AVAILABLE = False

# 修复Windows控制台UTF-8显示问题（支持星星★等特殊符号）
if sys.platform == 'win32':
    try:
        # 设置控制台代码页为UTF-8
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)  # UTF-8
        kernel32.SetConsoleCP(65001)

        # 重新包装stdout和stderr为UTF-8
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception as e:
        # 如果设置失败，尝试基本的UTF-8包装
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except:
            pass
        print(f"警告：控制台UTF-8设置可能不完整（{e}），某些符号可能无法正确显示")


# ============================================================================
# 【难度评分配置参数】 - 可以在这里调整所有评分参数
# ============================================================================

# 1. 覆盖率评分权重
WEIGHT_COVERAGE_500 = 10      # 前500字覆盖率权重
WEIGHT_COVERAGE_1000 = 10     # 前1000字覆盖率权重
WEIGHT_COVERAGE_1500 = 20     # 前1500字覆盖率权重

# 2. 字数需求评分权重
WEIGHT_CHARS_95 = 0          # 95%覆盖所需字数权重
WEIGHT_CHARS_99 = 0          # 99%覆盖所需字数权重

# 3. 字序评分权重
WEIGHT_ORDER_95 = 50          # 95%平均字序权重
WEIGHT_ORDER_99 = 30          # 99%平均字序权重

# 4. 字种数评分权重
WEIGHT_CHAR_TYPES = 10         # 字种数权重

# ===========================区间=================================================
# 5. 字数需求评分区间
CHARS_95_MIN = 300            # 95%覆盖字数下限（≤此值得0分）
CHARS_95_MAX = 2500           # 95%覆盖字数上限（≥此值得满分）
CHARS_99_MIN = 400           # 99%覆盖字数下限
CHARS_99_MAX = 4000           # 99%覆盖字数上限

# 6. 字序评分区间
ORDER_95_MIN = 400            # 95%平均字序下限（≤此值得0分，表示很常用）
ORDER_95_MAX = 2000           # 95%平均字序上限（≥此值得满分，表示很生僻）
ORDER_99_MIN = 500            # 99%平均字序下限
ORDER_99_MAX = 3000           # 99%平均字序上限

# 7. 字种数评分区间
CHAR_TYPES_BASELINE = 1500    # 字种数基准（常用字数量，超出此基准的才算难度）
                              # 此参数同时用于：
                              # 1. 字种数评分基准
                              # 2. 95%/99%覆盖字数的前N字判断（使用前1500.txt）
CHAR_TYPES_MIN = 0            # 超出基准的字种数下限（≤此值得0分）
CHAR_TYPES_MAX = 4500         # 超出基准的字种数上限（≥此值得满分）

# 8. 星级划分区间
STAR_THRESHOLD_1 = 20         # <20分为⭐
STAR_THRESHOLD_2 = 40         # <40分为⭐⭐
STAR_THRESHOLD_3 = 60         # <60分为⭐⭐⭐
STAR_THRESHOLD_4 = 80         # <80分为⭐⭐⭐⭐，≥80为⭐⭐⭐⭐⭐

# 9. 覆盖率评分方式
# True=直接线性映射(0-100%), False=使用区间映射
COVERAGE_LINEAR_MODE = True

# 如果使用区间映射模式，设置以下参数（当COVERAGE_LINEAR_MODE=False时生效）
COVERAGE_500_MIN = 65         # 前500字覆盖率下限
COVERAGE_500_MAX = 92         # 前500字覆盖率上限
COVERAGE_1000_MIN = 80        # 前1000字覆盖率下限
COVERAGE_1000_MAX = 98        # 前1000字覆盖率上限
COVERAGE_1500_MIN = 88        # 前1500字覆盖率下限
COVERAGE_1500_MAX = 99.5      # 前1500字覆盖率上限

# 10. 非线性加速系数（幂函数指数）
# 说明：
#   - 加速系数 = 1.0 时为线性
#   - 加速系数 > 1.0 时为减速增长
#   - 加速系数 < 1.0 时为加速增长（推荐1.5-3.0），数值越大增长越快
#   - 覆盖率：低覆盖率的书难度分数会加速增长
#   - 字序：高字序（生僻字）的书难度分数会加速增长
COVERAGE_ACCELERATION = 0.8   # 覆盖率加速系数（推荐1.5-3.0）
ORDER_ACCELERATION = 0.7      # 字序加速系数（推荐1.5-3.0）

# ============================================================================
# 以下是程序代码，一般不需要修改
# ============================================================================

# 输出文件夹名称
OUTPUT_FOLDER = "字频统计结果"


def display_width(text):
    """
    计算字符串的显示宽度（使用East Asian Width标准）
    - 全角/宽字符：宽度为2
    - 半角/窄字符：宽度为1
    """
    width = 0
    for char in text:
        # 获取字符的East Asian Width属性
        ea_width = unicodedata.east_asian_width(char)

        # F=Fullwidth, W=Wide: 宽度为2
        # A=Ambiguous: 在CJK环境中通常为2（包括★☆等符号）
        if ea_width in ('F', 'W', 'A'):
            width += 2
        # H=Halfwidth, Na=Narrow, N=Neutral: 宽度为1
        else:
            width += 1

    return width


class TableFormatter:
    """
    表格格式化器 - 使用固定列宽确保完美对齐
    """
    def __init__(self, headers, col_widths):
        """
        Args:
            headers: 表头列表，如 ['序号', '书名', '难度', '分数']
            col_widths: 固定列宽列表，如 [6, 50, 20, 10]
        """
        self.headers = headers
        self.rows = []
        self.col_widths = col_widths

    def add_row(self, *cols):
        """添加一行数据"""
        row = [str(col) for col in cols]
        self.rows.append(row)

    def _format_cell(self, text, target_width):
        """
        格式化单元格：截断或填充到固定宽度
        """
        text = str(text)
        current_width = display_width(text)

        # 如果超出宽度，截断
        if current_width > target_width:
            truncated = ""
            w = 0
            for ch in text:
                ea = unicodedata.east_asian_width(ch)
                ch_w = 2 if ea in ('F', 'W', 'A') else 1
                if w + ch_w > target_width:
                    break
                truncated += ch
                w += ch_w
            return truncated

        # 如果不足宽度，填充空格
        spaces_needed = target_width - current_width
        return text + ' ' * spaces_needed

    def format(self):
        """格式化输出整个表格"""
        lines = []
        total_width = sum(self.col_widths) + len(self.col_widths) - 1  # 加上列间空格

        # 表头
        header_parts = []
        for i, header in enumerate(self.headers):
            header_parts.append(self._format_cell(header, self.col_widths[i]))
        lines.append(' '.join(header_parts))

        # 分隔线
        lines.append('-' * total_width)

        # 数据行
        for row in self.rows:
            row_parts = []
            for i, col in enumerate(row):
                if i < len(self.col_widths):
                    row_parts.append(self._format_cell(col, self.col_widths[i]))
            lines.append(' '.join(row_parts))

        return '\n'.join(lines)


def format_row(col1, col2, col3, col4, width1=6, width2=52, width3=22, width4=10):
    """
    格式化一行数据，确保每列对齐

    Args:
        col1-col4: 各列内容（字符串）
        width1-width4: 各列的目标显示宽度

    Returns:
        格式化后的字符串
    """
    parts = []

    for col, target_width in [(col1, width1), (col2, width2), (col3, width3), (col4, width4)]:
        col_str = str(col)
        current_width = display_width(col_str)

        # 如果超出宽度，截断
        if current_width > target_width:
            truncated = ""
            w = 0
            for ch in col_str:
                ea = unicodedata.east_asian_width(ch)
                ch_w = 2 if ea in ('F', 'W', 'A') else 1
                if w + ch_w > target_width:
                    break
                truncated += ch
                w += ch_w
            col_str = truncated
            current_width = w

        # 计算需要填充多少空格
        spaces_needed = target_width - current_width
        parts.append(col_str + ' ' * spaces_needed)

    return ''.join(parts)


def ensure_output_folder():
    """确保输出文件夹存在，如果不存在则创建"""
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"创建输出文件夹: {OUTPUT_FOLDER}")
    return OUTPUT_FOLDER


def check_result_exists(file_path):
    """
    检查指定文件是否已有统计结果

    Args:
        file_path: 源文件路径

    Returns:
        bool: True表示已有结果，False表示没有结果
    """
    base_filename = os.path.basename(file_path)
    base_name = os.path.splitext(base_filename)[0]

    # 检查输出文件夹中是否存在对应的结果文件
    # 结果文件格式：书名_字频统计_难度xx.x.txt
    output_folder = OUTPUT_FOLDER
    if os.path.exists(output_folder):
        for existing_file in os.listdir(output_folder):
            # 检查文件名是否以书名开头，且包含"_字频统计_难度"
            if existing_file.startswith(base_name) and '_字频统计_难度' in existing_file:
                return True
    return False


def get_resource_path(relative_path):
    """获取资源文件的绝对路径，支持打包后的exe"""
    try:
        # PyInstaller创建临时文件夹，路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except AttributeError:
        # 没有打包，使用脚本所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


def find_txt_files(directory='books'):
    """
    找出指定目录下的所有txt文件（排除辅助文件和统计结果）

    Args:
        directory: 要搜索的目录，默认为 'books'

    Returns:
        list: txt文件列表
    """
    # 确保 books 目录存在
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            print(f"\n已创建 {directory} 目录")
            print(f"请将要统计的txt书籍文件放入 {directory} 目录中")
            print("=" * 70)
            return []
        except Exception as e:
            print(f"无法创建 {directory} 目录: {e}")
            return []

    txt_files = []
    # 需要排除的文件名（辅助文件）
    excluded_files = {'dict_simple.txt', '前1500.txt', 'dict.txt'}

    try:
        for file in os.listdir(directory):
            if file.endswith('.txt'):
                # 排除辅助文件、已生成的统计文件
                if (file not in excluded_files and
                    '_字频统计_难度' not in file and
                    not file.endswith('_字频统计.txt')):
                    # 返回相对于books目录的文件路径
                    txt_files.append(os.path.join(directory, file))
        return txt_files
    except Exception as e:
        print(f"读取 {directory} 目录失败: {e}")
        return []


def load_reference_chars():
    """
    加载参考字表（从前1500.txt）
    返回按顺序排列的1500个字的列表
    """
    ref_file = get_resource_path('前1500.txt')

    # 尝试多种编码
    encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030']

    for encoding in encodings:
        try:
            with open(ref_file, 'r', encoding=encoding) as f:
                content = f.read()

            # 提取所有中文字符（包括扩展区，保持顺序）
            chars = [
                char for char in content
                if ('\u4e00' <= char <= '\u9fff') or
                   ('\u3400' <= char <= '\u4dbf') or
                   ('\U00020000' <= char <= '\U0002ebef')
            ]
            if len(chars) > 0:
                print(f"  使用编码: {encoding}")
                return chars
        except (UnicodeDecodeError, UnicodeError, FileNotFoundError):
            continue

    print(f"⚠ 警告：无法加载前1500.txt（尝试了{len(encodings)}种编码）")
    print(f"   将使用dict_simple.txt的前1500个字作为替代方案")
    return None


def load_dict_order():
    """加载dict字序"""
    dict_file = get_resource_path('dict_simple.txt')

    # 尝试多种编码
    encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030']

    for encoding in encodings:
        try:
            with open(dict_file, 'r', encoding=encoding) as f:
                lines = f.readlines()

            char_order = {}
            for idx, line in enumerate(lines, start=1):
                char = line.strip()
                if char:
                    char_order[char] = idx

            print(f"  dict_simple.txt 使用编码: {encoding}")
            return char_order
        except (UnicodeDecodeError, UnicodeError, FileNotFoundError):
            continue

    print(f"加载dict字序失败（尝试了{len(encodings)}种编码）")
    print(f"尝试的路径: {dict_file}")
    return {}


def detect_encoding(file_path):
    """自动检测文件编码，使用chardet库提高准确性"""

    # 方法1: 尝试使用chardet库（如果已安装）
    try:
        import chardet

        # 读取文件的前100KB用于检测
        with open(file_path, 'rb') as f:
            raw_data = f.read(102400)  # 读取100KB

        # 使用chardet检测编码
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']

        # 如果置信度较高（>0.7），直接使用检测结果
        if confidence > 0.7 and encoding:
            # 标准化编码名称
            encoding = encoding.lower()
            if encoding in ['gb2312', 'gb18030']:
                encoding = 'gbk'  # 统一使用gbk
            elif encoding == 'ascii':
                encoding = 'utf-8'  # ASCII兼容UTF-8

            # 验证检测结果是否正确
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)
                print(f"  编码检测: {encoding.upper()} (置信度: {confidence:.0%})")
                return encoding
            except:
                pass
    except ImportError:
        # chardet未安装，使用备用方法
        pass
    except Exception as e:
        print(f"  编码检测警告: {e}")

    # 方法2: 备用方法 - 按优先级尝试常见编码
    # 先读取文件的前100KB内容用于检测(增加到100KB,减少UTF-8字符被截断的概率)
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(102400)  # 增加到100KB
    except:
        return None

    # 检测BOM标记
    if raw_data.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    elif raw_data.startswith(b'\xff\xfe') or raw_data.startswith(b'\xfe\xff'):
        return 'utf-16'

    # 按优先级尝试解码
    encodings_priority = [
        ('utf-8', 0),
        ('gbk', 0),
        ('gb18030', 0),
        ('big5', 0),
        ('utf-16', 0)
    ]

    valid_encodings = []

    for encoding, _ in encodings_priority:
        try:
            # 尝试解码全部内容
            decoded = raw_data.decode(encoding)

            # 统计中文字符比例（用于判断是否是正确的中文编码）
            chinese_count = sum(1 for c in decoded if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf')
            total_chars = len(decoded)
            chinese_ratio = chinese_count / total_chars if total_chars > 0 else 0

            # 如果中文字符比例较高，认为是有效编码
            if chinese_ratio > 0.3:  # 超过30%是中文
                valid_encodings.append((encoding, chinese_ratio))
            elif chinese_ratio > 0.1:  # 10-30%中文，也可能是正确的
                valid_encodings.append((encoding, chinese_ratio * 0.5))  # 降低权重
            elif encoding == 'utf-8' and chinese_ratio == 0:
                # 可能是纯英文或数字
                valid_encodings.append((encoding, 0.01))
        except (UnicodeDecodeError, UnicodeError):
            continue

    # 选择中文字符比例最高的编码
    if valid_encodings:
        valid_encodings.sort(key=lambda x: x[1], reverse=True)
        detected_encoding = valid_encodings[0][0]
        print(f"  编码检测: {detected_encoding.upper()} (中文比例: {valid_encodings[0][1]:.1%})")
        return detected_encoding

    # 如果没有找到合适的编码，使用改进的试错法
    print("  编码检测: 使用试错法...")
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'utf-16']

    # 读取文件内容用于测试
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(102400)  # 读取100KB
    except:
        return None

    best_encoding = None
    best_score = 0

    for encoding in encodings:
        try:
            # 尝试用errors='replace'解码，这样可以容忍轻微的编码错误
            decoded = raw_data.decode(encoding, errors='replace')

            # 统计成功解码的字符（非替换字符）
            replacement_char = '\ufffd'  # 这是errors='replace'使用的替换字符
            total_chars = len(decoded)
            replacement_count = decoded.count(replacement_char)
            success_rate = (total_chars - replacement_count) / total_chars if total_chars > 0 else 0

            # 统计中文字符比例
            chinese_count = sum(1 for c in decoded if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf')
            chinese_ratio = chinese_count / total_chars if total_chars > 0 else 0

            # 综合评分：成功率 * 0.6 + 中文比例 * 0.4
            score = success_rate * 0.6 + chinese_ratio * 0.4

            # 只接受成功率>95%且中文比例>30%的编码
            if success_rate > 0.95 and chinese_ratio > 0.3 and score > best_score:
                best_encoding = encoding
                best_score = score

        except (UnicodeDecodeError, UnicodeError):
            continue

    if best_encoding:
        print(f"  编码检测: {best_encoding.upper()} (置信度: {best_score:.0%})")
        return best_encoding

    # 如果所有编码都失败，返回None
    return None


def count_chars(file_path):
    """统计文件中每个字的出现次数，自动检测编码和繁简体"""
    print("\n正在检测文件编码...")

    # 先检测编码
    detected_encoding = detect_encoding(file_path)

    if detected_encoding is None:
        print(f"✗ 无法识别文件编码，尝试使用utf-8强制读取")
        detected_encoding = 'utf-8'
    else:
        print(f"✓ 检测完成: {detected_encoding.upper()}")

    try:
        with open(file_path, 'r', encoding=detected_encoding, errors='ignore') as f:
            content = f.read()

        # 提取中文字符并统计
        chinese_chars = [
            char for char in content
            if ('\u4e00' <= char <= '\u9fff') or  # 基本汉字
               ('\u3400' <= char <= '\u4dbf') or  # 扩展A区
               ('\U00020000' <= char <= '\U0002ebef')  # 扩展B-F区
        ]
        char_counter = Counter(chinese_chars)

        # 如果没有中文字符，直接返回
        if len(char_counter) == 0:
            return char_counter, detected_encoding

        # 检测繁简体：用统计出的字种判断
        print("正在检测繁简体...")
        try:
            import zhconv

            # 定义繁简对照表（常用特征字）
            TRAD_SIMP_PAIRS = {
                '為': '为', '無': '无', '來': '来', '會': '会', '學': '学', '國': '国',
                '過': '过', '時': '时', '間': '间', '現': '现', '說': '说', '個': '个',
                '這': '这', '還': '还', '開': '开', '關': '关', '東': '东', '當': '当',
                '對': '对', '們': '们', '應': '应', '處': '处', '業': '业', '進': '进',
                '種': '种', '將': '将', '產': '产', '電': '电', '機': '机', '實': '实',
                '發': '发', '題': '题', '經': '经', '體': '体', '點': '点', '從': '从',
                '見': '见', '動': '动', '問': '问', '長': '长', '認': '认', '與': '与',
                '後': '后', '萬': '万', '傳': '传', '車': '车', '書': '书', '買': '买',
                '賣': '卖', '變': '变', '戰': '战', '讓': '让', '嘗': '尝', '試': '试',
                '導': '导', '確': '确', '熱': '热', '環': '环', '雙': '双', '離': '离',
                '難': '难', '歷': '历', '場': '场', '聽': '听', '選': '选', '識': '识',
                '總': '总', '條': '条', '運': '运', '農': '农', '議': '议', '團': '团',
            }

            # 统计字种中繁简特征字的数量
            trad_count = sum(1 for c in char_counter.keys() if c in TRAD_SIMP_PAIRS)
            simp_count = sum(1 for c in char_counter.keys() if c in TRAD_SIMP_PAIRS.values())

            # 判断：繁体特征 > 简体特征 × 3
            is_traditional = trad_count > simp_count * 3 and trad_count > 10

            if is_traditional:
                print(f"✓ 检测到繁体文本（繁体特征字:{trad_count}个 > 简体:{simp_count}个）")
                print(f"  正在转换字种为简体...")
                # 转换字种：把 Counter 的 key 从繁体转为简体
                new_counter = Counter()
                for char, count in char_counter.items():
                    simplified_char = zhconv.convert(char, 'zh-cn')
                    new_counter[simplified_char] += count

                char_counter = new_counter
                print(f"✓ 转换完成，已将字种转为简体")
            else:
                print(f"✓ 检测到简体文本（繁体特征:{trad_count}个, 简体特征:{simp_count}个）")

        except ImportError:
            print("⚠ 未安装 zhconv，跳过繁简体检测")
            print("  提示：安装 zhconv 可自动处理繁体书籍")
            print("  安装命令: pip install zhconv")
        except Exception as e:
            print(f"⚠ 繁简体检测出错，按原文统计: {e}")

        return char_counter, detected_encoding

    except Exception as e:
        print(f"✗ 读取文件失败: {e}")
        return Counter(), None


def load_common_chars(reference_chars=None, char_order=None):
    """
    加载常用字表（前3500个字）
    - 前1500字：优先使用前1500.txt（如果可用）
    - 1500-3500字：使用dict_simple.txt按字序补充
    """
    common_chars = set()

    if reference_chars and len(reference_chars) > 0:
        # 前1500字使用前1500.txt
        common_chars = set(reference_chars)

        # 补充1500-3500字（从dict_simple.txt，按字序，排除前1500）
        reference_chars_set = set(reference_chars)
        remaining_needed = 3500 - len(reference_chars)

        if char_order and remaining_needed > 0:
            added_count = 0
            for char, order in sorted(char_order.items(), key=lambda x: x[1]):
                if char not in reference_chars_set:
                    common_chars.add(char)
                    added_count += 1
                    if added_count >= remaining_needed:
                        break
    else:
        # 回退方案：从dict_simple.txt读取前3500个字
        dict_file = get_resource_path('dict_simple.txt')
        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030']

        for encoding in encodings:
            try:
                with open(dict_file, 'r', encoding=encoding) as f:
                    for i, line in enumerate(f, 1):
                        if i > 3500:
                            break
                        char = line.strip()
                        if char:
                            common_chars.add(char)

                if len(common_chars) > 0:
                    return common_chars
            except (UnicodeDecodeError, UnicodeError, FileNotFoundError):
                continue

        print(f"加载常用字表失败（尝试了{len(encodings)}种编码）")

    return common_chars


def precompute_reference_sets(reference_chars, char_order, stats_ranges):
    """
    【性能优化】预计算所有需要的参考字表集合

    只计算一次，避免重复排序和遍历，大幅提升批量处理性能。

    时间复杂度：O(m log m) 一次性成本
    vs 原先：O(n × m log m) n=stats_ranges数量

    Args:
        reference_chars: 前1500字列表（来自前1500.txt）
        char_order: 字典序映射 {char: order}
        stats_ranges: 需要计算的区间列表 [10, 50, 100, ...]

    Returns:
        dict: {区间: set(字符集合)} 例如 {500: set('的一是...')}

    线程安全性：返回的所有set都是只读的，可安全共享
    """
    reference_sets_cache = {}

    if not reference_chars or len(reference_chars) == 0:
        # 回退方案：全部使用dict_simple.txt
        for top_n in stats_ranges:
            ref_set = {char for char, order in char_order.items() if order <= top_n}
            reference_sets_cache[top_n] = ref_set
        return reference_sets_cache

    # 【关键优化】预排序char_order（只排序一次！）
    # 避免每次calculate_coverage_stats都重复排序
    sorted_char_order = sorted(char_order.items(), key=lambda x: x[1])
    reference_chars_set = set(reference_chars)

    # 按区间从小到大处理（可以复用部分结果）
    for top_n in sorted(stats_ranges):
        ref_top_chars = set()

        if top_n <= len(reference_chars):
            # 直接从前1500.txt取前N个
            ref_top_chars = set(reference_chars[:top_n])
        else:
            # 前1500 + 从dict_simple.txt补充
            ref_top_chars = set(reference_chars)  # 复制全部1500个
            remaining_needed = top_n - len(reference_chars)
            added_count = 0

            # 使用预排序的结果，不再重复排序
            for char, order in sorted_char_order:
                if char not in reference_chars_set:
                    ref_top_chars.add(char)
                    added_count += 1
                    if added_count >= remaining_needed:
                        break

        # 存储为不可变frozenset（更安全，明确表示只读）
        reference_sets_cache[top_n] = frozenset(ref_top_chars)

    return reference_sets_cache


def calculate_coverage_stats_optimized(top_n, reference_sets_cache, char_counter, total_chars):
    """
    【性能优化】使用预计算集合的覆盖率计算函数

    直接使用预计算的字符集合，避免每次都重新排序char_order。

    时间复杂度：O(k) k=ref_top_chars大小
    vs 原先：O(m log m + k) m=char_order大小

    Args:
        top_n: 区间大小（如500, 1000）
        reference_sets_cache: 预计算的字符集合缓存
        char_counter: 当前文件的字频统计 Counter对象
        total_chars: 总字符数

    Returns:
        dict: {'actual_n', 'coverage', 'avg_count', 'total_count'}

    线程安全性：不修改任何共享数据，仅读取
    """
    ref_top_chars = reference_sets_cache.get(top_n, frozenset())

    # 【优化】使用sum和生成器表达式，比循环更高效
    top_count = sum(char_counter.get(char, 0) for char in ref_top_chars)

    coverage = (top_count / total_chars) * 100 if total_chars > 0 else 0
    avg_count = top_count / len(ref_top_chars) if len(ref_top_chars) > 0 else 0

    return {
        'actual_n': len(ref_top_chars),
        'coverage': coverage,
        'avg_count': avg_count,
        'total_count': top_count
    }


def analyze_rare_chars(char_counter, common_chars):
    """
    分析生僻字情况
    返回字典包含：
    - rare_chars: 所有生僻字列表 [(字, 次数)]
    - rare_char_count: 生僻字出现总次数
    - rare_char_ratio: 生僻字占文本比例
    - rare_type_count: 生僻字字种数
    - rare_type_ratio: 生僻字字种占比
    """
    rare_chars = []  # (字, 次数)
    common_char_count = 0
    rare_char_count = 0

    for char, count in char_counter.items():
        if char in common_chars:
            common_char_count += count
        else:
            rare_char_count += count
            rare_chars.append((char, count))

    # 按出现次数降序排序
    rare_chars.sort(key=lambda x: x[1], reverse=True)

    total_chars = common_char_count + rare_char_count
    rare_char_ratio = rare_char_count / total_chars if total_chars > 0 else 0
    rare_type_ratio = len(rare_chars) / len(char_counter) if len(char_counter) > 0 else 0

    return {
        'rare_chars': rare_chars,           # 所有生僻字列表
        'rare_char_count': rare_char_count, # 生僻字出现总次数
        'rare_char_ratio': rare_char_ratio, # 生僻字占文本比例
        'rare_type_count': len(rare_chars), # 生僻字字种数
        'rare_type_ratio': rare_type_ratio  # 生僻字字种占比
    }


def calculate_difficulty_rating(char_counter, total_chars, coverage_stats, cumulative_coverage, avg_order_95, avg_order_99, extra_char_types):
    """
    计算书籍难度（⭐-⭐⭐⭐⭐⭐）
    返回：(星级字符串, 分数0-100, 描述)

    所有评分参数可在文件开头的配置区域调整：
    - 权重分配：覆盖率46% + 字数25% + 字序20% + 字种9%
    - 评分区间：字数、字序、字种数的上下限
    - 星级划分：五个星级的分数阈值
    - 覆盖率模式：线性模式(0-100%)或区间模式
    """

    # 提取关键指标
    coverage_500 = coverage_stats.get(500, {}).get('coverage', 0)
    coverage_1000 = coverage_stats.get(1000, {}).get('coverage', 0)
    coverage_1500 = coverage_stats.get(1500, {}).get('coverage', 0)

    # 从cumulative_coverage获取95%和99%所需字数
    chars_for_95 = 0
    chars_for_99 = 0
    for target_pct, char_count, _ in cumulative_coverage:
        if target_pct == 95:
            chars_for_95 = char_count
        if target_pct == 99:
            chars_for_99 = char_count

    # 字种数
    char_type_count = len(char_counter)

    # 使用配置参数计算难度分数（0-100，越高越难）

    # 1-3. 覆盖率评分（应用非线性加速）
    if COVERAGE_LINEAR_MODE:
        # 线性模式：0%→满分（最难），100%→0分（最简单）
        # 应用加速系数：((100-coverage)/100)^COVERAGE_ACCELERATION
        score_500 = WEIGHT_COVERAGE_500 * (((100 - coverage_500) / 100) ** COVERAGE_ACCELERATION)
        score_1000 = WEIGHT_COVERAGE_1000 * (((100 - coverage_1000) / 100) ** COVERAGE_ACCELERATION)
        score_1500 = WEIGHT_COVERAGE_1500 * (((100 - coverage_1500) / 100) ** COVERAGE_ACCELERATION)
    else:
        # 区间模式：使用配置的区间范围
        if coverage_500 >= COVERAGE_500_MAX:
            score_500 = 0
        elif coverage_500 <= COVERAGE_500_MIN:
            score_500 = WEIGHT_COVERAGE_500
        else:
            ratio = (COVERAGE_500_MAX - coverage_500) / (COVERAGE_500_MAX - COVERAGE_500_MIN)
            score_500 = WEIGHT_COVERAGE_500 * (ratio ** COVERAGE_ACCELERATION)

        if coverage_1000 >= COVERAGE_1000_MAX:
            score_1000 = 0
        elif coverage_1000 <= COVERAGE_1000_MIN:
            score_1000 = WEIGHT_COVERAGE_1000
        else:
            ratio = (COVERAGE_1000_MAX - coverage_1000) / (COVERAGE_1000_MAX - COVERAGE_1000_MIN)
            score_1000 = WEIGHT_COVERAGE_1000 * (ratio ** COVERAGE_ACCELERATION)

        if coverage_1500 >= COVERAGE_1500_MAX:
            score_1500 = 0
        elif coverage_1500 <= COVERAGE_1500_MIN:
            score_1500 = WEIGHT_COVERAGE_1500
        else:
            ratio = (COVERAGE_1500_MAX - coverage_1500) / (COVERAGE_1500_MAX - COVERAGE_1500_MIN)
            score_1500 = WEIGHT_COVERAGE_1500 * (ratio ** COVERAGE_ACCELERATION)

    # 4. 95%覆盖所需字数评分
    if chars_for_95 <= CHARS_95_MIN:
        score_95_chars = 0
    elif chars_for_95 >= CHARS_95_MAX:
        score_95_chars = WEIGHT_CHARS_95
    else:
        score_95_chars = WEIGHT_CHARS_95 * (chars_for_95 - CHARS_95_MIN) / (CHARS_95_MAX - CHARS_95_MIN)

    # 5. 99%覆盖所需字数评分
    if chars_for_99 <= CHARS_99_MIN:
        score_99_chars = 0
    elif chars_for_99 >= CHARS_99_MAX:
        score_99_chars = WEIGHT_CHARS_99
    else:
        score_99_chars = WEIGHT_CHARS_99 * (chars_for_99 - CHARS_99_MIN) / (CHARS_99_MAX - CHARS_99_MIN)

    # 6. 95%平均字序评分（应用非线性加速）
    if avg_order_95 is None:
        score_95_order = WEIGHT_ORDER_95 / 2  # 默认中等难度
    elif avg_order_95 <= ORDER_95_MIN:
        score_95_order = 0
    elif avg_order_95 >= ORDER_95_MAX:
        score_95_order = WEIGHT_ORDER_95
    else:
        ratio = (avg_order_95 - ORDER_95_MIN) / (ORDER_95_MAX - ORDER_95_MIN)
        score_95_order = WEIGHT_ORDER_95 * (ratio ** ORDER_ACCELERATION)

    # 7. 99%平均字序评分（应用非线性加速）
    if avg_order_99 is None:
        score_99_order = WEIGHT_ORDER_99 / 2  # 默认中等难度
    elif avg_order_99 <= ORDER_99_MIN:
        score_99_order = 0
    elif avg_order_99 >= ORDER_99_MAX:
        score_99_order = WEIGHT_ORDER_99
    else:
        ratio = (avg_order_99 - ORDER_99_MIN) / (ORDER_99_MAX - ORDER_99_MIN)
        score_99_order = WEIGHT_ORDER_99 * (ratio ** ORDER_ACCELERATION)

    # 8. 字种数评分（使用传入的超出前1500.txt的字种数）
    if extra_char_types <= CHAR_TYPES_MIN:
        score_char_types = 0
    elif extra_char_types >= CHAR_TYPES_MAX:
        score_char_types = WEIGHT_CHAR_TYPES
    else:
        score_char_types = WEIGHT_CHAR_TYPES * (extra_char_types - CHAR_TYPES_MIN) / (CHAR_TYPES_MAX - CHAR_TYPES_MIN)

    # 综合难度分数（原始分数）
    raw_score = (score_500 + score_1000 + score_1500 +
                 score_95_chars + score_99_chars +
                 score_95_order + score_99_order + score_char_types)

    # 计算总权重
    total_weight = (WEIGHT_COVERAGE_500 + WEIGHT_COVERAGE_1000 + WEIGHT_COVERAGE_1500 +
                   WEIGHT_CHARS_95 + WEIGHT_CHARS_99 +
                   WEIGHT_ORDER_95 + WEIGHT_ORDER_99 +
                   WEIGHT_CHAR_TYPES)

    # 归一化到0-100（无论权重如何设置，最终都是0-100的标准分数）
    if total_weight > 0:
        difficulty_score = (raw_score / total_weight) * 100
    else:
        difficulty_score = 0

    # 转换为星级（20星制：每5分一个空心星☆，每10分一个实心星★）
    stars = difficulty_score_to_star_display(difficulty_score)

    # 返回详细信息
    score_details = {
        'coverage_500': (score_500, WEIGHT_COVERAGE_500, coverage_500),
        'coverage_1000': (score_1000, WEIGHT_COVERAGE_1000, coverage_1000),
        'coverage_1500': (score_1500, WEIGHT_COVERAGE_1500, coverage_1500),
        'chars_95': (score_95_chars, WEIGHT_CHARS_95, chars_for_95),
        'chars_99': (score_99_chars, WEIGHT_CHARS_99, chars_for_99),
        'order_95': (score_95_order, WEIGHT_ORDER_95, avg_order_95),
        'order_99': (score_99_order, WEIGHT_ORDER_99, avg_order_99),
        'char_types': (score_char_types, WEIGHT_CHAR_TYPES, extra_char_types),
        'raw_score': raw_score,
        'total_weight': total_weight
    }

    return stars, difficulty_score, score_details


def calculate_avg_char_order(chars_list, char_order):
    """
    计算一组字在字典中的平均序号
    用于评估这些字是否是常用字（序号靠前=更常用）

    参数：
    - chars_list: 字符列表 [(char, count), ...]
    - char_order: 字典序号映射 {char: order}

    返回：平均序号（不在字典中的字不计入）
    """
    orders = []
    for char, _ in chars_list:
        if char in char_order:
            orders.append(char_order[char])

    if orders:
        return sum(orders) / len(orders)
    else:
        return None


def print_main_menu():
    """打印主菜单"""
    print("\n" + "=" * 70)
    print("【字频统计与选书系统】")
    print("=" * 70)
    print("\n请选择功能：")
    print("  1. 复杂度计算 - 统计txt书籍的字频和难度")
    print("  2. 按分数筛选 - 根据难度分数筛选合适的书籍")
    print("  3. 搜书功能 - 根据书名模糊搜索书籍")
    print("  4. 难度排行榜 - 查看数据库中所有书籍的难度排行")
    print("  5. 95%字种数排行榜 - 查看95%覆盖所需字数排行")
    print("  6. 99%字种数排行榜 - 查看99%覆盖所需字数排行")
    print("  7. 95%平均字序排行榜 - 字序越小越常用")
    print("  8. 99%平均字序排行榜 - 字序越小越常用")
    print("  9. 总字种数排行榜 - 查看书籍总字种数排行")
    print("  0. 退出程序")
    print("=" * 70)


def get_db_connection():
    """获取数据库连接"""
    if not DB_UPLOAD_AVAILABLE:
        print("数据库功能不可用（未安装pymysql或db_uploader模块）")
        return None

    try:
        from db_uploader import load_db_config, check_db_connection, is_db_config_valid
        db_config = load_db_config()
        if not db_config:
            print("数据库配置文件不存在或读取失败")
            return None

        if not is_db_config_valid(db_config):
            print("数据库配置未填写或仍为模板占位符")
            return None

        success, db_conn = check_db_connection(db_config)
        if not success:
            print("数据库连接失败")
            return None

        return db_conn
    except Exception as e:
        print(f"数据库连接错误: {e}")
        return None


def difficulty_score_to_star_display(score):
    """将难度分数转换为星级显示（20级制：每5分一个空心星☆，每10分一个实心星★）"""
    # 计算有多少个5分单位
    units = int(score / 5)
    # 每2个单位合并成1个实心星，余数是空心星
    full_stars = units // 2  # 实心星数量
    half_star = units % 2    # 空心星数量（0或1）

    # 最多10个实心星
    full_stars = min(full_stars, 10)

    # 构建星级字符串
    result = "★" * full_stars
    if half_star and full_stars < 10:  # 只有在未满10个实心星时才加空心星
        result += "☆"

    # 如果什么都没有，至少显示一个空心星
    if not result:
        result = "☆"

    return result


def feature_generic_ranking(field_name, field_display_name, title, asc_desc, desc_desc,
                            show_difficulty=False, value_formatter=None):
    """
    通用排行榜功能（使用OFFSET分页，支持跳页）

    Args:
        field_name: 数据库字段名（如 'chars_95', 'difficulty_score'）
        field_display_name: 显示名称（如 '95%字数', '难度分值'）
        title: 排行榜标题（如 '95%字种数排行榜'）
        asc_desc: 正序说明（如 '从少到多，字数越少越简单'）
        desc_desc: 倒序说明（如 '从多到少，字数越多越难'）
        show_difficulty: 是否同时显示难度星级（默认False）
        value_formatter: 值格式化函数（如 lambda x: f"{x:.1f}"），默认为str
    """
    print("\n" + "=" * 70)
    print(f"【{title}】")
    print("=" * 70)

    # 获取数据库连接
    conn = get_db_connection()
    if not conn:
        input("\n按回车键返回主菜单...")
        return

    try:
        # 选择排序方式
        print("\n请选择排序方式：")
        print(f"  1. 正序（{asc_desc}）")
        print(f"  2. 倒序（{desc_desc}）[默认]")

        while True:
            order_choice = input("请选择 (1-2，直接回车默认倒序): ").strip()
            if order_choice == '':
                order_choice = '2'  # 默认倒序
            if order_choice in ['1', '2']:
                break
            print("无效输入，请输入1或2")

        is_ascending = (order_choice == '1')
        order_direction = "ASC" if is_ascending else "DESC"

        # 获取总记录数
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM book_difficulty")
        total_count = cursor.fetchone()[0]
        cursor.close()

        if total_count == 0:
            print("\n暂无数据！")
            input("\n按回车键返回主菜单...")
            return

        # 分页参数
        page_size = 20
        total_pages = (total_count + page_size - 1) // page_size
        current_page = 0

        while True:
            # 加载当前页数据
            cursor = conn.cursor()
            offset = current_page * page_size

            # 构建SQL查询
            select_fields = f"id, book_name, author, {field_name}"
            if show_difficulty:
                select_fields += ", difficulty_score, star_level"

            sql = f"""
                SELECT {select_fields}
                FROM book_difficulty
                ORDER BY {field_name} {order_direction}, id {order_direction}
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (page_size, offset))
            results = cursor.fetchall()
            cursor.close()

            if not results:
                if current_page == 0:
                    print("\n暂无数据！")
                    break
                else:
                    print("\n已经是最后一页了！")
                    current_page -= 1
                    continue

            # 显示结果
            print("\n" + "=" * 70)
            print(f"共 {total_pages} 页 | 第 {current_page + 1} 页（本页 {len(results)} 条 | 总 {total_count} 条）")
            print("=" * 70)

            # 根据是否显示难度调整表格列
            if show_difficulty:
                if field_name == 'difficulty_score':
                    headers = ['序号', '书名', '难度星级', field_display_name]
                    col_widths = [6, 48, 24, 10]
                else:
                    headers = ['序号', '书名', field_display_name, '难度星级']
                    col_widths = [6, 40, 12, 24]
            else:
                headers = ['序号', '书名', field_display_name]
                col_widths = [6, 52, 20]

            table = TableFormatter(headers, col_widths)

            for idx, row in enumerate(results, start=1):
                book_id, book_name, author, field_value = row[:4]

                # 格式化字段值
                if value_formatter:
                    formatted_value = value_formatter(field_value)
                else:
                    formatted_value = str(field_value) if field_value is not None else 'N/A'

                # 计算全局序号
                global_idx = current_page * page_size + idx

                if show_difficulty:
                    score, stars = row[4], row[5]
                    if '⭐' in stars:
                        stars = difficulty_score_to_star_display(score)

                    if field_name == 'difficulty_score':
                        table.add_row(str(global_idx), book_name, stars, formatted_value)
                    else:
                        table.add_row(str(global_idx), book_name, formatted_value, stars)
                else:
                    table.add_row(str(global_idx), book_name, formatted_value)

            print(table.format())

            # 翻页提示
            total_width = sum(table.col_widths) + len(table.col_widths) - 1
            print("-" * total_width)

            # 构建提示信息
            tips = []
            if current_page > 0:
                tips.append("- 上一页")
            if current_page < total_pages - 1:
                tips.append("= 下一页")
            tips.append("输入页码跳转")
            tips.append("回车返回")

            print("  " + " | ".join(tips))
            choice = input("请选择: ").strip()

            if choice == '-' and current_page > 0:
                current_page -= 1
            elif choice == '=' and current_page < total_pages - 1:
                current_page += 1
            elif choice == '':
                break
            else:
                # 尝试解析为页码
                try:
                    page_num = int(choice)
                    if 1 <= page_num <= total_pages:
                        current_page = page_num - 1
                    else:
                        print(f"页码超出范围，请输入 1-{total_pages} 之间的数字！")
                except ValueError:
                    pass

    except Exception as e:
        print(f"\n查询出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


# ============================================================================
# 各种排行榜功能（使用通用排行榜框架）
# ============================================================================

def feature_select_by_star():
    """功能2: 按分数筛选书籍"""
    print("\n" + "=" * 70)
    print("【按分数筛选书籍】")
    print("=" * 70)

    # 获取数据库连接
    conn = get_db_connection()
    if not conn:
        input("\n按回车键返回主菜单...")
        return

    try:
        # 用户输入分数范围
        print("\n请输入难度分数范围（0-100分）：")
        print("提示：分数越低越简单，分数越高越难")
        print()

        # 输入最低分
        while True:
            min_score_input = input("最低分数（直接回车默认0）: ").strip()
            if min_score_input == '':
                min_score = 0
                break
            try:
                min_score = float(min_score_input)
                if 0 <= min_score <= 100:
                    break
                print("请输入0-100之间的数字！")
            except ValueError:
                print("请输入有效的数字！")

        # 输入最高分
        while True:
            max_score_input = input("最高分数（直接回车默认100）: ").strip()
            if max_score_input == '':
                max_score = 100
                break
            try:
                max_score = float(max_score_input)
                if 0 <= max_score <= 100:
                    if max_score >= min_score:
                        break
                    print(f"最高分必须大于等于最低分（{min_score}）！")
                else:
                    print("请输入0-100之间的数字！")
            except ValueError:
                print("请输入有效的数字！")

        print(f"\n正在筛选难度分数在 {min_score:.1f} - {max_score:.1f} 之间的书籍...")

        # 获取总记录数
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM book_difficulty WHERE difficulty_score >= %s AND difficulty_score <= %s",
            (min_score, max_score)
        )
        total_count = cursor.fetchone()[0]
        cursor.close()

        if total_count == 0:
            print(f"\n未找到难度分数在 {min_score:.1f} - {max_score:.1f} 之间的书籍！")
            input("\n按回车键返回主菜单...")
            return

        # 分页参数
        page_size = 20
        total_pages = (total_count + page_size - 1) // page_size
        current_page = 0

        while True:
            # 加载当前页数据
            cursor = conn.cursor()
            offset = current_page * page_size
            sql = """
                SELECT id, book_name, author, difficulty_score, star_level
                FROM book_difficulty
                WHERE difficulty_score >= %s AND difficulty_score <= %s
                ORDER BY difficulty_score ASC, id ASC
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (min_score, max_score, page_size, offset))
            results = cursor.fetchall()
            cursor.close()

            if not results:
                if current_page == 0:
                    print("\n暂无数据！")
                    break
                else:
                    print("\n已经是最后一页了！")
                    current_page -= 1
                    continue

            # 显示结果
            print("\n" + "=" * 70)
            print(f"共 {total_pages} 页 | 第 {current_page + 1} 页（筛选条件：{min_score:.1f} - {max_score:.1f} 分 | 共 {total_count} 条）")
            print("=" * 70)

            # 表格格式
            headers = ['序号', '书名', '难度星级', '难度分值']
            col_widths = [6, 48, 24, 10]
            table = TableFormatter(headers, col_widths)

            for idx, row in enumerate(results, start=1):
                book_id, book_name, author, score, stars = row

                # 转换星级显示
                if '⭐' in stars:
                    stars = difficulty_score_to_star_display(score)

                table.add_row(str(current_page * page_size + idx), book_name, stars, f"{score:.1f}")

            print(table.format())

            # 翻页提示
            total_width = sum(col_widths) + len(col_widths) - 1
            print("-" * total_width)

            tips = []
            if current_page > 0:
                tips.append("- 上一页")
            if current_page < total_pages - 1:
                tips.append("= 下一页")
            tips.append("输入页码跳转")
            tips.append("回车返回")

            print("  " + " | ".join(tips))
            choice = input("请选择: ").strip()

            if choice == '-' and current_page > 0:
                current_page -= 1
            elif choice == '=' and current_page < total_pages - 1:
                current_page += 1
            elif choice == '':
                break
            else:
                # 尝试解析为页码
                try:
                    page_num = int(choice)
                    if 1 <= page_num <= total_pages:
                        current_page = page_num - 1
                    else:
                        print(f"页码超出范围，请输入 1-{total_pages} 之间的数字！")
                except ValueError:
                    pass

    except Exception as e:
        print(f"\n查询出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


def feature_difficulty_ranking():
    """功能3: 难度排行榜"""
    feature_generic_ranking(
        field_name='difficulty_score',
        field_display_name='难度分值',
        title='难度排行榜',
        asc_desc='从简单到困难',
        desc_desc='从困难到简单',
        show_difficulty=True,
        value_formatter=lambda x: f"{x:.1f}"
    )


def feature_chars_95_ranking():
    """功能4: 95%字种数排行榜"""
    feature_generic_ranking(
        field_name='chars_95',
        field_display_name='95%字数',
        title='95%字种数排行榜',
        asc_desc='从少到多，字数越少越简单',
        desc_desc='从多到少，字数越多越难',
        show_difficulty=False,
        value_formatter=lambda x: str(int(x)) if x is not None else 'N/A'
    )


def feature_chars_99_ranking():
    """功能5: 99%字种数排行榜"""
    feature_generic_ranking(
        field_name='chars_99',
        field_display_name='99%字数',
        title='99%字种数排行榜',
        asc_desc='从少到多，字数越少越简单',
        desc_desc='从多到少，字数越多越难',
        show_difficulty=False,
        value_formatter=lambda x: str(int(x)) if x is not None else 'N/A'
    )


def feature_avg_order_95_ranking():
    """功能6: 95%平均字序排行榜"""
    feature_generic_ranking(
        field_name='avg_order_95',
        field_display_name='95%平均字序',
        title='95%平均字序排行榜',
        asc_desc='从小到大，字序越小越常用',
        desc_desc='从大到小，字序越大越生僻',
        show_difficulty=False,
        value_formatter=lambda x: f"{x:.1f}" if x is not None else 'N/A'
    )


def feature_avg_order_99_ranking():
    """功能7: 99%平均字序排行榜"""
    feature_generic_ranking(
        field_name='avg_order_99',
        field_display_name='99%平均字序',
        title='99%平均字序排行榜',
        asc_desc='从小到大，字序越小越常用',
        desc_desc='从大到小，字序越大越生僻',
        show_difficulty=False,
        value_formatter=lambda x: f"{x:.1f}" if x is not None else 'N/A'
    )


def feature_char_types_ranking():
    """功能8: 总字种数排行榜"""
    feature_generic_ranking(
        field_name='char_types',
        field_display_name='总字种数',
        title='总字种数排行榜',
        asc_desc='从少到多，字种数越少字越简单',
        desc_desc='从多到少，字种数越多越复杂',
        show_difficulty=False,
        value_formatter=lambda x: str(int(x)) if x is not None else 'N/A'
    )


def feature_search_book():
    """功能3: 搜书功能（模糊搜索）"""
    print("\n" + "=" * 70)
    print("【搜书功能】")
    print("=" * 70)

    # 获取数据库连接
    conn = get_db_connection()
    if not conn:
        input("\n按回车键返回主菜单...")
        return

    try:
        # 用户输入搜索关键词
        keyword = input("\n请输入书名关键词（支持模糊搜索）: ").strip()

        if not keyword:
            print("关键词不能为空！")
            input("\n按回车键返回主菜单...")
            return

        # 模糊搜索 - 获取所有字段
        cursor = conn.cursor()
        sql = """
            SELECT id, book_name, author, difficulty_score, star_level,
                   char_types, char_types_in_1500, char_types_out_1500,
                   coverage_500, coverage_1000, coverage_1500,
                   avg_order_95, avg_order_99,
                   chars_95, chars_99,
                   chars_95_in_1500, chars_95_out_1500,
                   chars_99_in_1500, chars_99_out_1500,
                   total_chars, rare_char_types, rare_char_ratio,
                   file_name, tool_version
            FROM book_difficulty
            WHERE book_name LIKE %s
            ORDER BY difficulty_score ASC
        """
        cursor.execute(sql, (f'%{keyword}%',))
        results = cursor.fetchall()
        cursor.close()

        if not results:
            print(f"\n未找到包含 '{keyword}' 的书籍！")
            input("\n按回车键返回主菜单...")
            return

        # 显示搜索结果列表（简洁版）
        while True:
            print("\n" + "=" * 70)
            print(f"搜索到 {len(results)} 本书籍（关键词：{keyword}）")
            print("=" * 70)

            # 使用表格格式显示
            headers = ['序号', '书名', '难度星级', '难度分值']
            col_widths = [6, 48, 24, 10]
            table = TableFormatter(headers, col_widths)

            for idx, row in enumerate(results, start=1):
                book_id, book_name, author, score, stars = row[:5]

                # 转换星级显示
                if '⭐' in stars:
                    stars = difficulty_score_to_star_display(score)

                table.add_row(str(idx), book_name, stars, f"{score:.1f}")

            print(table.format())

            # 提示用户选择
            total_width = sum(col_widths) + len(col_widths) - 1
            print("-" * total_width)
            print("  输入序号查看详情 | 回车返回主菜单")

            choice = input("请选择: ").strip()

            if choice == '':
                break

            # 尝试解析为序号
            try:
                idx = int(choice)
                if 1 <= idx <= len(results):
                    # 显示详细信息
                    show_book_detail(results[idx - 1])
                else:
                    print(f"序号超出范围，请输入 1-{len(results)} 之间的数字！")
            except ValueError:
                print("请输入有效的数字！")

    except Exception as e:
        print(f"\n搜索出错: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键返回主菜单...")
    finally:
        conn.close()


def show_book_detail(row):
    """显示书籍详细信息"""
    # 解析数据
    (book_id, book_name, author, difficulty_score, star_level,
     char_types, char_types_in_1500, char_types_out_1500,
     coverage_500, coverage_1000, coverage_1500,
     avg_order_95, avg_order_99,
     chars_95, chars_99,
     chars_95_in_1500, chars_95_out_1500,
     chars_99_in_1500, chars_99_out_1500,
     total_chars, rare_char_types, rare_char_ratio,
     file_name, tool_version) = row

    # 转换星级显示
    if '⭐' in star_level:
        star_level = difficulty_score_to_star_display(difficulty_score)

    print("\n" + "=" * 70)
    print("【书籍详细信息】")
    print("=" * 70)

    # 基本信息
    print(f"\n📖 书名：{book_name}")
    if author:
        print(f"   作者：{author}")
    print(f"   文件名：{file_name}")
    print(f"   总字符数：{total_chars:,}")

    # 难度评估
    print("\n" + "-" * 70)
    print("【难度评估】")
    print("-" * 70)
    print(f"   难度星级：{star_level}")
    print(f"   难度分值：{difficulty_score:.1f} / 100")

    # 字种数分析
    print("\n" + "-" * 70)
    print("【字种数分析】")
    print("-" * 70)
    print(f"   总字种数：{char_types} 个")
    if char_types_in_1500 is not None and char_types_out_1500 is not None:
        print(f"   ├─ 前1500内：{char_types_in_1500} 个")
        print(f"   └─ 前1500外：{char_types_out_1500} 个")

    # 生僻字分析
    if rare_char_types is not None:
        print(f"\n   生僻字种数：{rare_char_types} 个", end="")
        if rare_char_ratio is not None:
            print(f"（占文本 {rare_char_ratio*100:.2f}%）")
        else:
            print()

    # 覆盖率分析
    print("\n" + "-" * 70)
    print("【高频字覆盖率】")
    print("-" * 70)
    if coverage_500 is not None:
        print(f"   前500字覆盖率：{coverage_500:.2f}%")
    if coverage_1000 is not None:
        print(f"   前1000字覆盖率：{coverage_1000:.2f}%")
    if coverage_1500 is not None:
        print(f"   前1500字覆盖率：{coverage_1500:.2f}%")

    # 累积覆盖分析
    print("\n" + "-" * 70)
    print("【累积覆盖分析】")
    print("-" * 70)

    # 95%覆盖
    if chars_95 is not None:
        print(f"   95%覆盖所需字数：{chars_95} 个")
        if chars_95_in_1500 is not None and chars_95_out_1500 is not None:
            print(f"   ├─ 前1500内：{chars_95_in_1500} 个")
            print(f"   └─ 前1500外：{chars_95_out_1500} 个")

    # 99%覆盖
    if chars_99 is not None:
        print(f"\n   99%覆盖所需字数：{chars_99} 个")
        if chars_99_in_1500 is not None and chars_99_out_1500 is not None:
            print(f"   ├─ 前1500内：{chars_99_in_1500} 个")
            print(f"   └─ 前1500外：{chars_99_out_1500} 个")

    # 平均字序分析
    print("\n" + "-" * 70)
    print("【平均字序分析】（字序越小=越常用）")
    print("-" * 70)
    if avg_order_95 is not None:
        print(f"   95%覆盖平均字序：{avg_order_95:.1f}")
    else:
        print(f"   95%覆盖平均字序：无数据")

    if avg_order_99 is not None:
        print(f"   99%覆盖平均字序：{avg_order_99:.1f}")
    else:
        print(f"   99%覆盖平均字序：无数据")

    # 工具版本
    if tool_version:
        print("\n" + "-" * 70)
        print(f"   统计工具版本：v{tool_version}")

    print("\n" + "=" * 70)
    input("\n按回车键返回搜索结果...")


# ============================================================================
# 书籍统计功能
# ============================================================================

def feature_book_statistics():
    """功能1: 书籍复杂度计算（原有功能）"""
    print("\n" + "=" * 70)
    print("【书籍复杂度计算】")
    print("=" * 70)

    # 1. 找出所有txt文件
    txt_files = find_txt_files()

    if not txt_files:
        print("\n" + "=" * 70)
        print("⚠ books目录中没有找到txt文件！")
        print("=" * 70)
        print("\n【使用说明】\n")
        print("本工具用于统计txt文件中的中文字符频率，并生成详细的统计报告。\n")
        print("📋 使用步骤：")
        print("  1. 将txt书籍文件放入 books 目录")
        print("  2. 双击运行本程序")
        print("  3. 根据提示选择要统计的txt文件（输入序号）")
        print("  4. 等待统计完成")
        print("  5. 统计结果会自动保存到 字频统计结果 目录\n")
        print("📊 统计内容包括：")
        print("  • 字种丰富度 - 衡量用字多样性")
        print("  • 用字均匀度 - 衡量各字使用是否平均")
        print("  • 字频集中度 - 衡量对常用字的依赖程度")
        print("  • 高频字覆盖率 - 前N个字覆盖多少文本")
        print("  • 累积覆盖率 - 覆盖X%文本需要多少字")
        print("  • 详细字频表 - 每个字的次数、占比、顺序\n")
        print("🔧 支持的编码格式：")
        print("  • UTF-8")
        print("  • GBK / GB2312 / GB18030（简体中文）")
        print("  • Big5（繁体中文）")
        print("  程序会自动识别编码，无需手动设置\n")
        print("💡 提示：")
        print("  • 只统计中文字符（汉字），标点符号和英文不计入")
        print("  • 统计大文件（>10MB）可能需要较长时间")
        print("  • 生成的统计文件可用任何文本编辑器打开查看\n")
        print("=" * 70)
        print("\n请将txt文件放到 books 目录后，重新运行程序！\n")
        input("按回车键返回主菜单...")
        return

    # 2. 对文件列表排序：未统计的排在前面
    txt_files_sorted = sorted(txt_files, key=lambda f: (check_result_exists(f), os.path.basename(f)))

    # 显示文件列表供用户选择
    print("\n找到以下txt文件（books目录）：")
    has_existing_results = False
    for idx, file_path in enumerate(txt_files_sorted, start=1):
        file_size = os.path.getsize(file_path) / 1024  # KB
        # 只显示文件名，不显示路径
        display_name = os.path.basename(file_path)
        # 检查是否已有结果
        if check_result_exists(file_path):
            print(f"{idx}. {display_name} ({file_size:.2f} KB) [已有结果]")
            has_existing_results = True
        else:
            print(f"{idx}. {display_name} ({file_size:.2f} KB)")

    if has_existing_results:
        print("\n💡 提示：标记为[已有结果]的文件在批量扫描时将自动跳过")

    # 3. 用户选择
    while True:
        try:
            choice = input(f"\n请选择要统计的文件 (1-{len(txt_files_sorted)}，输入'all'扫描所有，输入0返回): ")
            if choice == '0':
                return

            # 处理"all"选项 - 扫描所有txt文件
            if choice.lower() == 'all':
                print("\n" + "=" * 70)
                print("开始批量扫描所有txt文件...")
                print("=" * 70)

                # 过滤掉已有结果的文件
                files_to_process = [f for f in txt_files_sorted if not check_result_exists(f)]
                skipped_count = len(txt_files_sorted) - len(files_to_process)

                if skipped_count > 0:
                    print(f"跳过 {skipped_count} 个已有结果的文件")

                if not files_to_process:
                    print("所有文件都已有统计结果，无需重复计算！")
                    input("\n按回车键返回主菜单...")
                    return

                print(f"找到 {len(files_to_process)} 个文件需要统计\n")

                # 【性能优化】批量模式：预加载共享数据，避免每个文件重复加载
                print("=" * 70)
                print("【性能优化】正在预加载共享参考数据...")
                print("=" * 70)

                # 加载前1500字表
                print("  ⏳ 加载前1500.txt...")
                shared_reference_chars = load_reference_chars()
                if shared_reference_chars:
                    print(f"  ✓ 已加载 {len(shared_reference_chars)} 个参考字")
                else:
                    print("  ⚠ 未找到前1500.txt，将使用dict_simple.txt")

                # 加载字典序
                print("  ⏳ 加载dict_simple.txt...")
                shared_char_order = load_dict_order()
                print(f"  ✓ 已加载 {len(shared_char_order)} 个字的字典序")

                # 加载常用字集合
                print("  ⏳ 构建常用字集合...")
                shared_common_chars = load_common_chars(shared_reference_chars, shared_char_order)
                print(f"  ✓ 已构建 {len(shared_common_chars)} 个常用字集合")

                # 【关键优化】预计算所有区间的参考字表集合
                print("  ⏳ 预计算参考字表集合（这是性能提升的关键）...")
                stats_ranges = [10, 50, 100, 500, 1000, 1500, 2000, 3000, 5000]
                shared_reference_sets = precompute_reference_sets(
                    shared_reference_chars, shared_char_order, stats_ranges
                )
                print(f"  ✓ 已预计算 {len(stats_ranges)} 个区间的字表集合")

                print("=" * 70)
                print("✓ 共享数据加载完成！批量处理将大幅提速")
                print("=" * 70)
                print()

                # 【性能监控】记录批量处理开始时间
                import time
                batch_start_time = time.time()

                # 初始化数据库连接（批量模式）
                db_conn = None
                db_config = None
                existing_books = None  # 【批量优化】已存在书籍缓存
                pending_inserts = []   # 【批量优化】待插入列表
                pending_updates = []   # 【批量优化】待更新列表
                batch_threshold = 10   # 【批量优化】批量阈值：每积累10条数据执行一次SQL

                if DB_UPLOAD_AVAILABLE:
                    try:
                        from db_uploader import load_db_config, check_db_connection, is_db_config_valid, load_existing_books, batch_insert_books, batch_update_books
                        db_config = load_db_config()
                        if db_config and is_db_config_valid(db_config):
                            success, db_conn = check_db_connection(db_config)
                            if success:
                                print("✓ 数据库连接成功，批量上传模式已启用")
                                # 【批量优化】预加载已存在的书籍列表
                                print("  ⏳ 正在加载已存在书籍列表...")
                                existing_books = load_existing_books(db_conn)
                                print(f"  ✓ 已加载 {len(existing_books)} 本书籍缓存\n")
                            else:
                                print("⚠ 数据库连接失败，将跳过数据库上传\n")
                        else:
                            print("⚠ 数据库配置未填写，将跳过数据库上传\n")
                    except Exception as e:
                        print(f"⚠ 数据库初始化失败: {e}，将跳过数据库上传\n")

                # 定义批量提交函数
                def flush_pending_data():
                    """【批量优化】提交待处理的数据到数据库"""
                    nonlocal pending_inserts, pending_updates
                    insert_count = 0
                    update_count = 0

                    if pending_inserts:
                        insert_count = batch_insert_books(db_conn, pending_inserts)
                        if insert_count > 0:
                            print(f"    ✓ 批量插入 {insert_count} 条记录")
                        pending_inserts = []

                    if pending_updates:
                        update_count = batch_update_books(db_conn, pending_updates)
                        if update_count > 0:
                            print(f"    ✓ 批量更新 {update_count} 条记录")
                        pending_updates = []

                    return insert_count + update_count

                # 存储所有书籍的统计结果用于汇总
                summary_results = []
                upload_success_count = 0
                upload_skip_count = 0

                for idx, file_path in enumerate(files_to_process, start=1):
                    display_name = os.path.basename(file_path)
                    print(f"\n{'='*70}")
                    print(f"[{idx}/{len(files_to_process)}] 正在处理: {display_name}")
                    print("-" * 70)

                    # 【性能优化】传递共享数据给process_file
                    result = process_file(
                        file_path,
                        batch_mode=True,
                        db_conn=db_conn,
                        db_config=db_config,
                        existing_books=existing_books,  # 【批量优化】传递缓存
                        shared_reference_chars=shared_reference_chars,
                        shared_char_order=shared_char_order,
                        shared_common_chars=shared_common_chars,
                        shared_reference_sets=shared_reference_sets
                    )
                    if result:
                        summary_results.append(result)

                        # 【批量优化】处理数据库上传数据
                        if 'db_prepared_data' in result and result['db_prepared_data']:
                            if result['db_is_update']:
                                pending_updates.append(result['db_prepared_data'])
                            else:
                                pending_inserts.append(result['db_prepared_data'])

                        # 更新数据库连接（可能在process_file中被更新）
                        if 'db_conn' in result and result['db_conn'] is not None:
                            db_conn = result['db_conn']

                        # 统计上传情况
                        upload_status = ""
                        if 'upload_success' in result:
                            if result['upload_success']:
                                upload_success_count += 1
                                upload_status = " | 准备上传"
                            else:
                                upload_skip_count += 1
                                upload_status = " | 跳过上传"

                        # 打印完成信息
                        print(f"✓ [{idx}/{len(files_to_process)}] 完成: {display_name} (字种数: {result['char_type_count']}, 难度: {result['difficulty_score']:.1f}分{upload_status})")

                        # 【批量优化】达到批量阈值时，批量提交
                        total_pending = len(pending_inserts) + len(pending_updates)
                        if total_pending >= batch_threshold and db_conn:
                            print(f"\n  【批量提交】已积累 {total_pending} 条数据，开始批量处理...")
                            affected = flush_pending_data()
                            if affected > 0:
                                print(f"  【批量提交】成功处理 {affected} 条记录\n")
                    else:
                        print(f"✗ [{idx}/{len(files_to_process)}] 失败: {display_name}")
                    print("="*70)

                # 【批量优化】处理剩余的待提交数据
                if db_conn and (pending_inserts or pending_updates):
                    total_pending = len(pending_inserts) + len(pending_updates)
                    print(f"\n{'='*70}")
                    print(f"【最终批量提交】处理剩余 {total_pending} 条数据...")
                    print("="*70)
                    affected = flush_pending_data()
                    if affected > 0:
                        print(f"✓ 成功处理 {affected} 条记录\n")

                # 关闭数据库连接
                if db_conn:
                    try:
                        db_conn.close()
                        print("✓ 数据库连接已关闭\n")
                    except:
                        pass

                # 生成汇总报告
                if summary_results:
                    generate_summary_report(summary_results)

                # 【性能监控】计算并显示批量处理性能统计
                batch_end_time = time.time()
                total_time = batch_end_time - batch_start_time
                avg_time_per_file = total_time / len(files_to_process) if len(files_to_process) > 0 else 0

                print("\n" + "=" * 70)
                print("批量扫描完成！")
                print("=" * 70)
                print(f"统计书籍: {len(summary_results)} 本")
                # 如果数据库连接成功过，显示上传统计
                if DB_UPLOAD_AVAILABLE and (upload_success_count > 0 or upload_skip_count > 0):
                    print(f"数据库上传: 成功 {upload_success_count} 个，跳过 {upload_skip_count} 个")
                print("-" * 70)
                print("【性能统计】")
                print(f"  总耗时: {total_time:.2f} 秒")
                print(f"  平均每本: {avg_time_per_file:.2f} 秒")
                if len(files_to_process) > 0:
                    print(f"  处理速度: {3600/avg_time_per_file:.1f} 本/小时")
                print("=" * 70)
                input("\n按回车键返回主菜单...")
                return

            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(txt_files_sorted):
                selected_file = txt_files_sorted[choice_idx]
                break
            else:
                print("输入的数字超出范围，请重新输入！")
        except ValueError:
            print("输入无效，请输入数字或'all'！")

    # 执行统计
    process_file(selected_file)
    input("\n按回车键返回主菜单...")


def main():
    print("=" * 50)
    print("字频统计工具")
    print(f"版本: {TOOL_VERSION}")
    print("=" * 50)

    # 0. 确保输出文件夹存在
    ensure_output_folder()

    # 检查编码检测库
    try:
        import chardet
        print("\n✓ 已安装 chardet 库，将使用高精度编码检测")
    except ImportError:
        print("\n⚠ 未安装 chardet 库，将使用基础编码检测")
        print("  建议安装以提高编码检测准确率: pip install chardet")

    # 主循环：显示功能菜单
    while True:
        print_main_menu()

        choice = input("\n请选择功能 (0-9): ").strip()

        if choice == '0':
            print("\n感谢使用！")
            break
        elif choice == '1':
            # 书籍复杂度计算
            feature_book_statistics()
        elif choice == '2':
            # 按分数筛选书籍
            feature_select_by_star()
        elif choice == '3':
            # 搜书功能
            feature_search_book()
        elif choice == '4':
            # 难度排行榜
            feature_difficulty_ranking()
        elif choice == '5':
            # 95%字种数排行榜
            feature_chars_95_ranking()
        elif choice == '6':
            # 99%字种数排行榜
            feature_chars_99_ranking()
        elif choice == '7':
            # 95%平均字序排行榜
            feature_avg_order_95_ranking()
        elif choice == '8':
            # 99%平均字序排行榜
            feature_avg_order_99_ranking()
        elif choice == '9':
            # 总字种数排行榜
            feature_char_types_ranking()
        else:
            print("\n无效选择，请输入0-9之间的数字")


def process_file(selected_file, batch_mode=False, db_conn=None, db_config=None, existing_books=None,
                 shared_reference_chars=None, shared_char_order=None,
                 shared_common_chars=None, shared_reference_sets=None):
    """处理单个文件的统计

    Args:
        selected_file: 文件名
        batch_mode: 是否批量模式（True时自动上传，不询问确认）
        db_conn: 复用的数据库连接（批量模式用）
        db_config: 数据库配置（批量模式用）
        existing_books: 【批量优化】已存在书籍缓存 {(book_name, author): book_id}
        shared_reference_chars: 【性能优化】共享的前1500字列表（避免重复加载）
        shared_char_order: 【性能优化】共享的字典序映射（避免重复加载）
        shared_common_chars: 【性能优化】共享的常用字集合（避免重复加载）
        shared_reference_sets: 【性能优化】预计算的参考字表集合（避免重复计算）

    线程安全性：所有shared_*参数都是只读的，不会被修改
    """
    print(f"\n正在统计文件: {selected_file}")

    # 4. 统计字频
    char_counter, file_encoding = count_chars(selected_file)
    total_chars = sum(char_counter.values())

    if total_chars == 0:
        print("文件中没有找到中文字符！")
        return

    print(f"共统计到 {total_chars} 个中文字符")
    print(f"不重复字符数: {len(char_counter)}")

    # 【性能优化】5. 加载参考字表和字序 - 优先使用共享数据
    if shared_reference_chars is not None:
        reference_chars = shared_reference_chars
        if not batch_mode:  # 非批量模式才打印（避免刷屏）
            print(f"\n使用共享参考字表（前1500.txt），共 {len(reference_chars)} 个字")
    else:
        print("\n正在加载参考字表（前1500.txt）...")
        reference_chars = load_reference_chars()
        if reference_chars:
            print(f"加载了参考字表，共 {len(reference_chars)} 个字")
        else:
            print("使用dict_simple.txt作为替代")

    if shared_char_order is not None:
        char_order = shared_char_order
        if not batch_mode:
            print(f"使用共享字典序，共 {len(char_order)} 个字的顺序")
    else:
        print("正在加载dict.yaml...")
        char_order = load_dict_order()
        print(f"加载了 {len(char_order)} 个字的顺序")

    # 6. 排序：按照dict.yaml的顺序排序
    # 在dict.yaml中的字按顺序排列，不在的字放在最后按出现次数降序排列
    chars_in_dict = []
    chars_not_in_dict = []

    for char, count in char_counter.items():
        if char in char_order:
            chars_in_dict.append((char, count, char_order[char]))
        else:
            chars_not_in_dict.append((char, count))

    # 在字典中的字按字序排序
    chars_in_dict.sort(key=lambda x: x[2])
    # 不在字典中的字按出现次数降序排序
    chars_not_in_dict.sort(key=lambda x: x[1], reverse=True)

    # 6.5 计算文字散列度指标
    # 按出现次数降序排列所有字符（用于计算累积覆盖率）
    all_chars_by_freq = sorted(char_counter.items(), key=lambda x: x[1], reverse=True)

    # 【性能优化】计算不同区间的统计 - 使用预计算的集合或现场计算
    stats_ranges = [10, 50, 100, 500, 1000, 1500, 2000, 3000, 5000]
    coverage_stats = {}

    if shared_reference_sets is not None:
        # 批量模式：使用预计算的集合，避免重复排序
        for n in stats_ranges:
            coverage_stats[n] = calculate_coverage_stats_optimized(
                n, shared_reference_sets, char_counter, total_chars
            )
    else:
        # 单文件模式：现场计算（也比旧版快，因为用了优化的算法）
        # 预计算一次参考集合
        local_reference_sets = precompute_reference_sets(reference_chars, char_order, stats_ranges)
        for n in stats_ranges:
            coverage_stats[n] = calculate_coverage_stats_optimized(
                n, local_reference_sets, char_counter, total_chars
            )

    # 【性能优化】计算累积覆盖率（覆盖X%的文本需要多少字）
    # 使用标志位代替any()查找，从O(n²)优化到O(n)
    cumulative_coverage = []
    cumulative_count = 0
    thresholds = {50: False, 80: False, 90: False, 95: False, 99: False}

    for idx, (char, count) in enumerate(all_chars_by_freq, start=1):
        cumulative_count += count
        coverage_pct = (cumulative_count / total_chars) * 100

        # O(1)检查和标记，避免重复的any()查找
        for threshold in [50, 80, 90, 95, 99]:
            if not thresholds[threshold] and coverage_pct >= threshold:
                cumulative_coverage.append((threshold, idx, coverage_pct))
                thresholds[threshold] = True

        # 提前退出：所有阈值都找到了，无需继续遍历
        if all(thresholds.values()):
            break

    # 100%覆盖就是所有字种数
    cumulative_coverage.append((100, len(char_counter), 100.0))

    # 6.6 形码用户专属分析
    # 【性能优化】优先使用共享的常用字集合
    if shared_common_chars is not None:
        common_chars = shared_common_chars
        if not batch_mode:
            print(f"使用共享常用字表，共 {len(common_chars)} 个常用字")
    else:
        print("\n正在加载常用字表...")
        common_chars = load_common_chars(reference_chars, char_order)
        print(f"加载了 {len(common_chars)} 个常用字")

    print("正在分析生僻字...")
    rare_analysis = analyze_rare_chars(char_counter, common_chars)

    # 计算95%和99%覆盖的平均字序
    print("正在计算平均字序...")
    chars_for_95_pct = 0
    chars_for_99_pct = 0
    for target_pct, char_count, _ in cumulative_coverage:
        if target_pct == 95:
            chars_for_95_pct = char_count
        if target_pct == 99:
            chars_for_99_pct = char_count

    # 获取达到95%和99%所需的字
    chars_for_95_list = all_chars_by_freq[:chars_for_95_pct] if chars_for_95_pct > 0 else []
    chars_for_99_list = all_chars_by_freq[:chars_for_99_pct] if chars_for_99_pct > 0 else []

    # 计算平均字序
    avg_order_95 = calculate_avg_char_order(chars_for_95_list, char_order)
    avg_order_99 = calculate_avg_char_order(chars_for_99_list, char_order)

    # 计算超出前1500.txt的字种数
    print("正在计算超出前1500的字种数...")
    if reference_chars:
        reference_chars_set = set(reference_chars)
        extra_char_types = sum(1 for char in char_counter.keys() if char not in reference_chars_set)

        # 计算95%和99%覆盖字数中前1500内外的分布
        chars_95_in_ref = sum(1 for char, _ in chars_for_95_list if char in reference_chars_set)
        chars_95_out_ref = len(chars_for_95_list) - chars_95_in_ref
        chars_99_in_ref = sum(1 for char, _ in chars_for_99_list if char in reference_chars_set)
        chars_99_out_ref = len(chars_for_99_list) - chars_99_in_ref
    else:
        # 如果没有前1500.txt，使用CHAR_TYPES_BASELINE作为基准
        extra_char_types = max(0, len(char_counter) - CHAR_TYPES_BASELINE)
        chars_95_in_ref = 0
        chars_95_out_ref = 0
        chars_99_in_ref = 0
        chars_99_out_ref = 0

    print("正在计算书籍难度...")
    stars, difficulty_score, score_details = calculate_difficulty_rating(
        char_counter, total_chars, coverage_stats, cumulative_coverage, avg_order_95, avg_order_99, extra_char_types
    )

    # 7. 输出结果到文件（只使用文件名，不包含路径）
    base_filename = os.path.basename(selected_file)  # 去掉路径，只保留文件名
    output_filename = f"{os.path.splitext(base_filename)[0]}_字频统计_难度{difficulty_score:.1f}.txt"
    output_file = os.path.join(OUTPUT_FOLDER, output_filename)

    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入表头
        f.write("=" * 80 + "\n")
        f.write("【书籍难度分析报告】\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"文件名: {base_filename}\n")
        f.write(f"文件编码: {file_encoding.upper() if file_encoding else '未知'}\n")
        f.write(f"总字符数: {total_chars}\n")
        f.write(f"字种数: {len(char_counter)} 个（其中前1500内: {len(char_counter) - extra_char_types} 个，前1500外: {extra_char_types} 个）\n")
        f.write("=" * 80 + "\n\n")

        # ========== 核心评估指标（形码用户最关心） ==========
        f.write("【核心评估指标】\n")
        f.write("=" * 80 + "\n\n")

        # 1. 书籍难度评级
        f.write(f"1. 书籍难度评级\n")
        f.write(f"   {stars}  （难度分数：{difficulty_score:.1f}/100）\n\n")
        f.write(f"   评估维度：\n")

        # 只显示权重>0的维度
        if WEIGHT_CHAR_TYPES > 0:
            f.write(f"     • 字种数：{len(char_counter)} 个（前1500内: {len(char_counter) - extra_char_types} 个，前1500外: {extra_char_types} 个）\n")

        if WEIGHT_COVERAGE_500 > 0:
            f.write(f"     • 前500字覆盖率：{coverage_stats[500]['coverage']:.2f}%\n")
        if WEIGHT_COVERAGE_1000 > 0:
            f.write(f"     • 前1000字覆盖率：{coverage_stats[1000]['coverage']:.2f}%\n")
        if WEIGHT_COVERAGE_1500 > 0:
            f.write(f"     • 前1500字覆盖率：{coverage_stats[1500]['coverage']:.2f}%\n")

        # 找出95%和99%所需字数
        chars_95, chars_99 = 0, 0
        for target_pct, char_count, _ in cumulative_coverage:
            if target_pct == 95:
                chars_95 = char_count
            if target_pct == 99:
                chars_99 = char_count

        if WEIGHT_CHARS_95 > 0:
            f.write(f"     • 95%覆盖所需字数：{chars_95} 个（前{CHAR_TYPES_BASELINE}内: {chars_95_in_ref}，前{CHAR_TYPES_BASELINE}外: {chars_95_out_ref}）\n")
        if WEIGHT_CHARS_99 > 0:
            f.write(f"     • 99%覆盖所需字数：{chars_99} 个（前{CHAR_TYPES_BASELINE}内: {chars_99_in_ref}，前{CHAR_TYPES_BASELINE}外: {chars_99_out_ref}）\n")

        # 添加平均字序
        if WEIGHT_ORDER_95 > 0:
            if avg_order_95 is not None:
                f.write(f"     • 95%平均字序：{avg_order_95:.1f}  （字序越小=越常用）\n")
            else:
                f.write(f"     • 95%平均字序：无数据\n")

        if WEIGHT_ORDER_99 > 0:
            if avg_order_99 is not None:
                f.write(f"     • 99%平均字序：{avg_order_99:.1f}  （字序越小=越常用）\n")
            else:
                f.write(f"     • 99%平均字序：无数据\n")
        f.write("\n")
        f.write(f"   💡 说明：\n")
        # 动态计算权重分配（只显示非0权重）
        total_weight = score_details['total_weight']
        if total_weight > 0:
            weight_parts = []
            coverage_weight = WEIGHT_COVERAGE_500 + WEIGHT_COVERAGE_1000 + WEIGHT_COVERAGE_1500
            if coverage_weight > 0:
                coverage_pct = coverage_weight / total_weight * 100
                weight_parts.append(f"覆盖率{coverage_pct:.0f}%")

            chars_weight = WEIGHT_CHARS_95 + WEIGHT_CHARS_99
            if chars_weight > 0:
                chars_pct = chars_weight / total_weight * 100
                weight_parts.append(f"字数{chars_pct:.0f}%")

            order_weight = WEIGHT_ORDER_95 + WEIGHT_ORDER_99
            if order_weight > 0:
                order_pct = order_weight / total_weight * 100
                weight_parts.append(f"字序{order_pct:.0f}%")

            if WEIGHT_CHAR_TYPES > 0:
                types_pct = WEIGHT_CHAR_TYPES / total_weight * 100
                weight_parts.append(f"字种{types_pct:.0f}%")

            f.write(f"     - 权重分配：{' + '.join(weight_parts)}\n")
        else:
            f.write(f"     - 权重分配：未设置\n")
        f.write("\n")

        # 2. 生僻字分析
        f.write(f"2. 生僻字分析\n")
        f.write(f"   生僻字字种数：{rare_analysis['rare_type_count']} 个（占字种{rare_analysis['rare_type_ratio']*100:.2f}%）\n")
        f.write(f"   生僻字出现次数：{rare_analysis['rare_char_count']} 次（占文本{rare_analysis['rare_char_ratio']*100:.2f}%）\n")
        f.write(f"   说明：生僻字指不在常用3500字内的字，打字时可能需要查编码\n")

        # 显示前20个最常见的生僻字
        if rare_analysis['rare_chars']:
            f.write(f"\n   最常见的生僻字（前20个）：\n")
            top_rare = rare_analysis['rare_chars'][:20]
            for i in range(0, len(top_rare), 10):
                chars_line = "、".join([f"{char}({count})" for char, count in top_rare[i:i+10]])
                f.write(f"   {chars_line}\n")

        f.write("\n" + "=" * 80 + "\n\n")

        # 高频字覆盖率分析 - 使用TableFormatter
        f.write("【高频字覆盖率分析】\n")
        coverage_table = TableFormatter(
            ['区间', '累计次数', '覆盖率', '平均出现次数'],
            [12, 15, 15, 15]
        )
        for n in stats_ranges:
            stats = coverage_stats[n]
            coverage_table.add_row(
                f"前{n}",
                str(stats['total_count']),
                f"{stats['coverage']:.2f}%",
                f"{stats['avg_count']:.1f}"
            )

        # 输出表格，每行前面加3个空格缩进
        for line in coverage_table.format().split('\n'):
            f.write(f"   {line}\n")

        # 1. 累积覆盖率分析 - 使用TableFormatter
        f.write(f"\n1. 累积覆盖率分析\n")
        cumulative_table = TableFormatter(['覆盖率', '所需字数'], [15, 15])
        for target_pct, char_count, actual_pct in cumulative_coverage:
            cumulative_table.add_row(f"{actual_pct:.2f}%", str(char_count))

        # 输出表格，每行前面加3个空格缩进
        for line in cumulative_table.format().split('\n'):
            f.write(f"   {line}\n")

        # 2. 最高频字分析
        f.write(f"\n2. 最高频字分析\n")
        top_char, top_count = all_chars_by_freq[0]
        top_pct = (top_count / total_chars) * 100
        f.write(f"   最高频字: '{top_char}' 出现 {top_count} 次，占比 {top_pct:.2f}%\n")

        if len(all_chars_by_freq) >= 3:
            top3_count = sum(count for char, count in all_chars_by_freq[:3])
            top3_pct = (top3_count / total_chars) * 100
            top3_chars = '、'.join([char for char, count in all_chars_by_freq[:3]])
            f.write(f"   前3个字: {top3_chars}，累计占比 {top3_pct:.2f}%\n")

        if len(all_chars_by_freq) >= 10:
            top10_count = sum(count for char, count in all_chars_by_freq[:10])
            top10_pct = (top10_count / total_chars) * 100
            f.write(f"   前10个字: 累计占比 {top10_pct:.2f}%\n")

        # 3. 低频字分析
        f.write(f"\n3. 低频字分析\n")
        once_chars = [char for char, count in char_counter.items() if count == 1]
        twice_chars = [char for char, count in char_counter.items() if count == 2]
        low_freq_chars = [char for char, count in char_counter.items() if count <= 5]

        f.write(f"   仅出现1次的字: {len(once_chars)} 个 ({len(once_chars)/len(char_counter)*100:.2f}%)\n")
        f.write(f"   仅出现2次的字: {len(twice_chars)} 个 ({len(twice_chars)/len(char_counter)*100:.2f}%)\n")
        f.write(f"   出现≤5次的字: {len(low_freq_chars)} 个 ({len(low_freq_chars)/len(char_counter)*100:.2f}%)\n")

        f.write("\n" + "=" * 80 + "\n\n")

        # 添加详细算式展示（只显示权重>0的维度）
        f.write(f"   📊 难度计算详情：\n")
        f.write(f"   ------------------------------------------------------------------\n")

        # 覆盖率维度
        coverage_weight = WEIGHT_COVERAGE_500 + WEIGHT_COVERAGE_1000 + WEIGHT_COVERAGE_1500
        if coverage_weight > 0:
            score_500, weight_500, val_500 = score_details['coverage_500']
            score_1000, weight_1000, val_1000 = score_details['coverage_1000']
            score_1500, weight_1500, val_1500 = score_details['coverage_1500']
            coverage_total = score_500 + score_1000 + score_1500
            coverage_pct = coverage_weight / total_weight * 100 if total_weight > 0 else 0

            f.write(f"   【覆盖率维度】 (权重 {coverage_pct:.0f}%)\n")
            if COVERAGE_LINEAR_MODE:
                f.write(f"     评分标准: 0%→满分 (最难), 100%→0分 (最简单), 加速系数={COVERAGE_ACCELERATION}\n")
            else:
                f.write(f"     评分标准: 区间模式, 500字({COVERAGE_500_MIN}%-{COVERAGE_500_MAX}%), ")
                f.write(f"1000字({COVERAGE_1000_MIN}%-{COVERAGE_1000_MAX}%), ")
                f.write(f"1500字({COVERAGE_1500_MIN}%-{COVERAGE_1500_MAX}%)\n")

            if weight_500 > 0:
                f.write(f"     前500字覆盖: {val_500:.1f}% → 得分 {score_500:.2f}/{weight_500}\n")
            if weight_1000 > 0:
                f.write(f"     前1000字覆盖: {val_1000:.1f}% → 得分 {score_1000:.2f}/{weight_1000}\n")
            if weight_1500 > 0:
                f.write(f"     前1500字覆盖: {val_1500:.1f}% → 得分 {score_1500:.2f}/{weight_1500}\n")
            f.write(f"     小计: {coverage_total:.2f}\n\n")

        # 字数维度
        chars_weight = WEIGHT_CHARS_95 + WEIGHT_CHARS_99
        if chars_weight > 0:
            score_95c, weight_95c, val_95c = score_details['chars_95']
            score_99c, weight_99c, val_99c = score_details['chars_99']
            chars_total = score_95c + score_99c
            chars_pct = chars_weight / total_weight * 100 if total_weight > 0 else 0

            f.write(f"   【字数维度】 (权重 {chars_pct:.0f}%)\n")
            f.write(f"     评分标准: 95%区间[{CHARS_95_MIN}-{CHARS_95_MAX}字], 99%区间[{CHARS_99_MIN}-{CHARS_99_MAX}字]\n")
            if weight_95c > 0:
                f.write(f"     95%覆盖字数: {val_95c} 个 → 得分 {score_95c:.2f}/{weight_95c}\n")
            if weight_99c > 0:
                f.write(f"     99%覆盖字数: {val_99c} 个 → 得分 {score_99c:.2f}/{weight_99c}\n")
            f.write(f"     小计: {chars_total:.2f}\n\n")

        # 字序维度
        order_weight = WEIGHT_ORDER_95 + WEIGHT_ORDER_99
        if order_weight > 0:
            score_95o, weight_95o, val_95o = score_details['order_95']
            score_99o, weight_99o, val_99o = score_details['order_99']
            order_total = score_95o + score_99o
            order_pct = order_weight / total_weight * 100 if total_weight > 0 else 0

            f.write(f"   【字序维度】 (权重 {order_pct:.0f}%)\n")
            f.write(f"     评分标准: 95%区间[{ORDER_95_MIN}-{ORDER_95_MAX}], 99%区间[{ORDER_99_MIN}-{ORDER_99_MAX}], 加速系数={ORDER_ACCELERATION}\n")
            if weight_95o > 0:
                if val_95o is not None:
                    f.write(f"     95%平均字序: {val_95o:.1f} → 得分 {score_95o:.2f}/{weight_95o}\n")
                else:
                    f.write(f"     95%平均字序: 无数据 → 得分 {score_95o:.2f}/{weight_95o}\n")
            if weight_99o > 0:
                if val_99o is not None:
                    f.write(f"     99%平均字序: {val_99o:.1f} → 得分 {score_99o:.2f}/{weight_99o}\n")
                else:
                    f.write(f"     99%平均字序: 无数据 → 得分 {score_99o:.2f}/{weight_99o}\n")
            f.write(f"     小计: {order_total:.2f}\n\n")

        # 字种维度
        if WEIGHT_CHAR_TYPES > 0:
            score_types, weight_types, val_types = score_details['char_types']
            types_pct = WEIGHT_CHAR_TYPES / total_weight * 100 if total_weight > 0 else 0

            f.write(f"   【字种维度】 (权重 {types_pct:.0f}%)\n")
            f.write(f"     评分标准: 前{CHAR_TYPES_BASELINE}字外的字种数, 区间[{CHAR_TYPES_MIN}-{CHAR_TYPES_MAX}个]\n")
            f.write(f"     前1500外字种: {val_types} 个 → 得分 {score_types:.2f}/{weight_types}\n")
            f.write(f"     小计: {score_types:.2f}\n\n")

        # 总分计算
        raw_score = score_details['raw_score']
        f.write(f"   【总分计算】\n")
        f.write(f"     原始得分: {raw_score:.2f}\n")
        f.write(f"     总权重: {total_weight:.2f}\n")
        f.write(f"     归一化公式: (原始得分 / 总权重) × 100\n")
        f.write(f"     最终难度: ({raw_score:.2f} / {total_weight:.2f}) × 100 = {difficulty_score:.1f} 分\n")
        f.write(f"   ------------------------------------------------------------------\n")
        f.write("\n")

        # 写入详细字频表
        f.write("【详细字频统计表】\n")
        f.write("=" * 80 + "\n")
        f.write(f"{'字':<5}{'次数':<10}{'比例(%)':<12}{'原次序':<10}\n")
        f.write("=" * 80 + "\n")

        # 写入在dict.yaml中的字
        for char, count, order in chars_in_dict:
            percentage = (count / total_chars) * 100
            f.write(f"{char:<5}{count:<10}{percentage:<12.2f}{order:<10}\n")

        # 写入不在dict.yaml中的字
        if chars_not_in_dict:
            f.write("\n" + "-" * 80 + "\n")
            f.write("以下字符不在dict.yaml中（按出现次数降序排列）:\n")
            f.write("-" * 80 + "\n")
            for char, count in chars_not_in_dict:
                percentage = (count / total_chars) * 100
                f.write(f"{char:<5}{count:<10}{percentage:<12.2f}{'N/A':<10}\n")

        # 强制刷新缓冲区，确保数据立即写入磁盘
        f.flush()
        os.fsync(f.fileno())

    print(f"\n统计完成！结果已保存到: {output_file}")

    # 显示核心评估指标
    print("\n" + "=" * 70)
    print("【核心评估指标】")
    print("=" * 70)
    print(f"文件: {base_filename}")
    print(f"书籍难度: {stars}  ({difficulty_score:.1f}/100)")
    print(f"字种数: {len(char_counter)} 个（前1500内: {len(char_counter) - extra_char_types}，前1500外: {extra_char_types}）")
    print(f"生僻字: {rare_analysis['rare_type_count']} 个（{rare_analysis['rare_type_ratio']*100:.1f}%）")
    print(f"\n覆盖率分析:")
    print(f"  前500字:  {coverage_stats[500]['coverage']:.1f}%")
    print(f"  前1000字: {coverage_stats[1000]['coverage']:.1f}%")
    print(f"  前1500字: {coverage_stats[1500]['coverage']:.1f}%")

    # 找出95%和99%的数据
    chars_95, chars_99 = 0, 0
    for target_pct, char_count, _ in cumulative_coverage:
        if target_pct == 95:
            chars_95 = char_count
        if target_pct == 99:
            chars_99 = char_count

    print(f"\n累积覆盖:")
    print(f"  95%: {chars_95}个字", end="")
    if avg_order_95:
        print(f" (平均字序 {avg_order_95:.0f})")
    else:
        print()
    print(f"  99%: {chars_99}个字", end="")
    if avg_order_99:
        print(f" (平均字序 {avg_order_99:.0f})")
    else:
        print()

    print("\n" + "=" * 70)

    # 数据库上传（可选功能）
    upload_success = False
    db_prepared_data = None
    db_is_update = False

    if DB_UPLOAD_AVAILABLE:
        try:
            if batch_mode:
                # 【批量优化】批量模式：只准备数据，不执行SQL
                success, returned_conn, prepared_data, is_update = handle_database_upload(
                    base_filename, total_chars, char_counter, coverage_stats,
                    avg_order_95, avg_order_99, chars_95, chars_99,
                    chars_95_in_ref, chars_95_out_ref, chars_99_in_ref, chars_99_out_ref,
                    extra_char_types, difficulty_score, stars, rare_analysis,
                    tool_version=TOOL_VERSION,
                    batch_mode=True,
                    db_conn=db_conn,
                    db_config=db_config,
                    existing_books=existing_books  # 传递缓存
                )
                upload_success = success
                db_prepared_data = prepared_data
                db_is_update = is_update
                if returned_conn is not None:
                    db_conn = returned_conn
            else:
                # 单文件模式：立即执行SQL
                success, returned_conn = handle_database_upload(
                    base_filename, total_chars, char_counter, coverage_stats,
                    avg_order_95, avg_order_99, chars_95, chars_99,
                    chars_95_in_ref, chars_95_out_ref, chars_99_in_ref, chars_99_out_ref,
                    extra_char_types, difficulty_score, stars, rare_analysis,
                    tool_version=TOOL_VERSION,
                    batch_mode=False,
                    db_conn=db_conn,
                    db_config=db_config
                )
                upload_success = success
                if returned_conn is not None:
                    db_conn = returned_conn

            # 返回数据库连接和准备好的数据
            return {
                'filename': base_filename,
                'total_chars': total_chars,
                'char_type_count': len(char_counter),
                'extra_char_types': extra_char_types,
                'rare_type_count': rare_analysis['rare_type_count'],
                'rare_type_ratio': rare_analysis['rare_type_ratio'],
                'coverage_500': coverage_stats[500]['coverage'],
                'coverage_1000': coverage_stats[1000]['coverage'],
                'coverage_1500': coverage_stats[1500]['coverage'],
                'chars_95': chars_95,
                'chars_99': chars_99,
                'avg_order_95': avg_order_95,
                'avg_order_99': avg_order_99,
                'difficulty_score': difficulty_score,
                'stars': stars,
                'tool_version': TOOL_VERSION,
                'db_conn': db_conn,
                'db_config': db_config,
                'upload_success': upload_success,
                'db_prepared_data': db_prepared_data,  # 【批量优化】准备好的数据
                'db_is_update': db_is_update  # 【批量优化】是否更新操作
            }
        except Exception as e:
            print(f"\n数据库上传出错（已跳过）: {e}")

    # 返回统计结果用于汇总报告
    return {
        'filename': base_filename,
        'total_chars': total_chars,
        'char_type_count': len(char_counter),
        'extra_char_types': extra_char_types,  # 超出前1500的字种数
        'rare_type_count': rare_analysis['rare_type_count'],
        'rare_type_ratio': rare_analysis['rare_type_ratio'],
        'coverage_500': coverage_stats[500]['coverage'],
        'coverage_1000': coverage_stats[1000]['coverage'],
        'coverage_1500': coverage_stats[1500]['coverage'],
        'chars_95': chars_95,
        'chars_99': chars_99,
        'avg_order_95': avg_order_95,
        'avg_order_99': avg_order_99,
        'difficulty_score': difficulty_score,
        'stars': stars,
        'tool_version': TOOL_VERSION,
        'upload_success': upload_success
    }


def generate_summary_report(results):
    """生成所有书籍的汇总报告"""
    output_file = os.path.join(OUTPUT_FOLDER, "【汇总报告】所有书籍难度对比.txt")

    # 按难度分数排序
    results_sorted = sorted(results, key=lambda x: x['difficulty_score'])

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("【所有书籍难度汇总报告】\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"统计时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"统计书籍数: {len(results)} 本\n")
        f.write("=" * 80 + "\n\n")

        # 按难度排序的表格
        f.write("【按难度排序】\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'排名':<6}{'书名':<30}{'难度':<8}{'分数':<10}{'字种数':<10}{'生僻字':<10}\n")
        f.write("-" * 80 + "\n")

        for idx, r in enumerate(results_sorted, start=1):
            # 截断过长的文件名
            filename = r['filename'][:28] + '..' if len(r['filename']) > 30 else r['filename']
            f.write(f"{idx:<6}{filename:<30}{r['stars']:<8}{r['difficulty_score']:<10.1f}"
                   f"{r['char_type_count']:<10}{r['rare_type_count']:<10}\n")

        f.write("\n" + "=" * 80 + "\n\n")

        # 详细对比表
        f.write("【详细数据对比】\n")
        f.write("-" * 80 + "\n")

        for r in results_sorted:
            f.write(f"\n📖 {r['filename']}\n")
            f.write(f"   难度: {r['stars']}  ({r['difficulty_score']:.1f}/100)\n")
            f.write(f"   字种数: {r['char_type_count']} 个（前1500内: {r['char_type_count'] - r['extra_char_types']}，前1500外: {r['extra_char_types']}）\n")
            f.write(f"   生僻字: {r['rare_type_count']} 个 ({r['rare_type_ratio']*100:.1f}%)\n")
            f.write(f"   覆盖率: 前500字={r['coverage_500']:.1f}% | "
                   f"前1000字={r['coverage_1000']:.1f}% | "
                   f"前1500字={r['coverage_1500']:.1f}%\n")
            f.write(f"   累积覆盖: 95%需{r['chars_95']}字 | 99%需{r['chars_99']}字\n")
            if r['avg_order_95'] and r['avg_order_99']:
                f.write(f"   平均字序: 95%={r['avg_order_95']:.0f} | 99%={r['avg_order_99']:.0f}\n")
            f.write("\n")

        f.write("=" * 80 + "\n\n")

        # 统计分析
        f.write("【统计分析】\n")
        f.write("-" * 80 + "\n")

        scores = [r['difficulty_score'] for r in results]
        f.write(f"平均难度: {sum(scores)/len(scores):.1f}分\n")
        f.write(f"最简单: {results_sorted[0]['filename']} ({results_sorted[0]['difficulty_score']:.1f}分)\n")
        f.write(f"最困难: {results_sorted[-1]['filename']} ({results_sorted[-1]['difficulty_score']:.1f}分)\n")
        f.write(f"难度跨度: {results_sorted[-1]['difficulty_score'] - results_sorted[0]['difficulty_score']:.1f}分\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("💡 说明：难度评分综合考虑字种数、覆盖率、字数需求、字序等多个维度\n")
        f.write("=" * 80 + "\n")

    print(f"\n汇总报告已生成: {output_file}")
    print(f"共统计 {len(results)} 本书籍")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print("\n" + "=" * 70)
        print("程序出现错误：")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 70)
        input("\n按回车键退出...")
