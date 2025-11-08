#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# author: 虎码新手2群-也无风雨也无晴
"""
数据库上传模块 - 将字频统计结果上传到MySQL数据库
"""

import os
import re


def parse_book_info_from_filename(filename):
    """
    从文件名提取书名

    简化版本：直接使用整个文件名（去掉前缀编号和扩展名）作为书名
    不再尝试识别作者，作者统一设为None

    支持的前缀格式：
    - "001_书名.txt" → 书名
    - "01.书名.txt" → 书名
    - "1-书名.txt" → 书名

    Args:
        filename: 文件名（不含路径）

    Returns:
        tuple: (书名, None)
    """
    # 移除扩展名
    name = os.path.splitext(filename)[0]

    # 移除常见的前缀数字编号（如 001_、01.、1-等）
    # 匹配：开头的数字、空格、点、下划线、横线
    name = re.sub(r'^[\d\s\.。_\-]+', '', name)

    # 清理首尾空格
    name = name.strip()

    # 返回书名和None作者
    return name, None


def check_book_exists(conn, book_name, author):
    """
    检查数据库中是否已存在该书籍记录

    Args:
        conn: 数据库连接
        book_name: 书名
        author: 作者名（可为None）

    Returns:
        bool: 存在返回True
    """
    try:
        cursor = conn.cursor()

        if author:
            sql = "SELECT COUNT(*) FROM book_difficulty WHERE book_name = %s AND author = %s"
            cursor.execute(sql, (book_name, author))
        else:
            sql = "SELECT COUNT(*) FROM book_difficulty WHERE book_name = %s AND author IS NULL"
            cursor.execute(sql, (book_name,))

        count = cursor.fetchone()[0]
        cursor.close()

        return count > 0
    except Exception as e:
        print(f"查重失败: {e}")
        return False


def load_db_config():
    """
    加载数据库配置文件

    打包后的逻辑：
    1. 优先从exe同目录加载配置（用户可修改）
    2. 如果不存在，从打包的模板文件生成配置和SQL到exe目录
    3. 提示用户修改配置文件

    Returns:
        dict: 配置字典，失败返回None
    """
    import sys
    import shutil

    config_filename = 'db_config.yaml'
    template_filename = 'db_config.yaml.template'
    sql_filename = 'create_table.sql'

    # 如果是打包后的exe
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        user_config_file = os.path.join(exe_dir, config_filename)
        user_template_file = os.path.join(exe_dir, template_filename)
        user_sql_file = os.path.join(exe_dir, sql_filename)

        # 打包资源路径（临时解压目录，只读）
        bundled_config_file = os.path.join(sys._MEIPASS, config_filename)
        bundled_template_file = os.path.join(sys._MEIPASS, template_filename)
        bundled_sql_file = os.path.join(sys._MEIPASS, sql_filename)

        # 首次运行：生成模板文件和SQL文件到exe目录（给用户参考）
        if not os.path.exists(user_template_file) and os.path.exists(bundled_template_file):
            try:
                shutil.copy2(bundled_template_file, user_template_file)
                print(f"\n✓ 已生成配置模板: {user_template_file}")
            except:
                pass

        if not os.path.exists(user_sql_file) and os.path.exists(bundled_sql_file):
            try:
                shutil.copy2(bundled_sql_file, user_sql_file)
                print(f"✓ 已生成SQL文件: {user_sql_file}")
            except:
                pass

        # 读取配置优先级：
        # 1. exe同目录的 db_config.yaml（用户自己配置的，最高优先级）
        # 2. 打包在exe里的 db_config.yaml（开发者配置，默认fallback）
        if os.path.exists(user_config_file):
            config_file = user_config_file
        elif os.path.exists(bundled_config_file):
            config_file = bundled_config_file
        else:
            return None
    else:
        # 开发模式：从模板生成配置文件
        base_path = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(base_path, config_filename)
        template_file = os.path.join(base_path, template_filename)

        # 如果真实配置不存在但模板存在，从模板生成
        if not os.path.exists(config_file) and os.path.exists(template_file):
            try:
                shutil.copy2(template_file, config_file)
                print(f"✓ 已从模板生成配置文件: {config_file}")
                print("💡 如需使用数据库功能，请编辑此文件填写真实的数据库连接信息\n")
            except Exception as e:
                print(f"⚠ 无法生成配置文件: {e}")
                # 生成失败，直接使用模板（只读）
                config_file = template_file

    if not os.path.exists(config_file):
        return None

    try:
        import yaml
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return None


def is_db_config_valid(config):
    """
    检查数据库配置是否已正确填写（非模板占位符）

    Args:
        config: 数据库配置字典

    Returns:
        bool: 配置有效返回True，仍为模板占位符返回False
    """
    if not config or 'mysql' not in config:
        return False

    mysql = config['mysql']

    # 检查是否仍为模板占位符
    placeholder_values = ['your_username', 'your_password', 'your_database']

    if mysql.get('user') in placeholder_values:
        return False
    if mysql.get('password') in placeholder_values:
        return False
    if mysql.get('database') in placeholder_values:
        return False

    return True


def check_db_connection(config):
    """
    检查数据库连接

    Args:
        config: 数据库配置字典

    Returns:
        tuple: (bool, connection) 连接成功返回(True, conn)，失败返回(False, None)
    """
    try:
        import pymysql
        conn = pymysql.connect(
            host=config['mysql']['host'],
            port=config['mysql']['port'],
            user=config['mysql']['user'],
            password=config['mysql']['password'],
            database=config['mysql']['database'],
            charset=config['mysql']['charset']
        )
        return True, conn
    except ImportError:
        print("错误：未安装 pymysql 模块")
        print("请运行: pip install pymysql")
        return False, None
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return False, None


def upload_to_database(conn, data):
    """
    上传统计数据到数据库

    Args:
        conn: 数据库连接
        data: 统计数据字典

    Returns:
        bool: 上传成功返回True
    """
    try:
        cursor = conn.cursor()

        # 插入数据
        sql = """
        INSERT INTO book_difficulty (
            book_name, author, char_types, char_types_in_1500, char_types_out_1500,
            coverage_500, coverage_1000, coverage_1500,
            avg_order_95, avg_order_99,
            chars_95, chars_99,
            chars_95_in_1500, chars_95_out_1500,
            chars_99_in_1500, chars_99_out_1500,
            difficulty_score, star_level,
            file_name, total_chars,
            rare_char_types, rare_char_ratio,
            tool_version
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s
        )
        """

        values = (
            data['book_name'],
            data['author'],
            data['char_types'],
            data['char_types_in_1500'],
            data['char_types_out_1500'],
            data['coverage_500'],
            data['coverage_1000'],
            data['coverage_1500'],
            data['avg_order_95'],
            data['avg_order_99'],
            data['chars_95'],
            data['chars_99'],
            data['chars_95_in_1500'],
            data['chars_95_out_1500'],
            data['chars_99_in_1500'],
            data['chars_99_out_1500'],
            data['difficulty_score'],
            data['star_level'],
            data['file_name'],
            data['total_chars'],
            data['rare_char_types'],
            data['rare_char_ratio'],
            data['tool_version']
        )

        cursor.execute(sql, values)
        conn.commit()

        inserted_id = cursor.lastrowid

        cursor.close()

        print(f"  ✓ 已上传: {data['book_name']}" + (f" ({data['author']})" if data['author'] else "") + f" [ID: {inserted_id}]")
        return True

    except Exception as e:
        print(f"  ✗ 上传失败: {e}")
        return False


def update_database(conn, data):
    """
    更新数据库中的统计数据

    Args:
        conn: 数据库连接
        data: 统计数据字典

    Returns:
        bool: 更新成功返回True
    """
    try:
        cursor = conn.cursor()

        # 更新数据
        sql = """
        UPDATE book_difficulty SET
            char_types = %s,
            char_types_in_1500 = %s,
            char_types_out_1500 = %s,
            coverage_500 = %s,
            coverage_1000 = %s,
            coverage_1500 = %s,
            avg_order_95 = %s,
            avg_order_99 = %s,
            chars_95 = %s,
            chars_99 = %s,
            chars_95_in_1500 = %s,
            chars_95_out_1500 = %s,
            chars_99_in_1500 = %s,
            chars_99_out_1500 = %s,
            difficulty_score = %s,
            star_level = %s,
            file_name = %s,
            total_chars = %s,
            rare_char_types = %s,
            rare_char_ratio = %s,
            tool_version = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE book_name = %s AND (author = %s OR (author IS NULL AND %s IS NULL))
        """

        values = (
            data['char_types'],
            data['char_types_in_1500'],
            data['char_types_out_1500'],
            data['coverage_500'],
            data['coverage_1000'],
            data['coverage_1500'],
            data['avg_order_95'],
            data['avg_order_99'],
            data['chars_95'],
            data['chars_99'],
            data['chars_95_in_1500'],
            data['chars_95_out_1500'],
            data['chars_99_in_1500'],
            data['chars_99_out_1500'],
            data['difficulty_score'],
            data['star_level'],
            data['file_name'],
            data['total_chars'],
            data['rare_char_types'],
            data['rare_char_ratio'],
            data['tool_version'],
            data['book_name'],
            data['author'],
            data['author']
        )

        cursor.execute(sql, values)
        conn.commit()

        affected_rows = cursor.rowcount
        cursor.close()

        print(f"  ✓ 已更新: {data['book_name']}" + (f" ({data['author']})" if data['author'] else "") + f" [影响行数: {affected_rows}]")
        return True

    except Exception as e:
        print(f"  ✗ 更新失败: {e}")
        return False


def prepare_upload_data(
    book_name, author, selected_file, total_chars, char_counter, coverage_stats,
    avg_order_95, avg_order_99, chars_95, chars_99, chars_95_in_ref, chars_95_out_ref,
    chars_99_in_ref, chars_99_out_ref, extra_char_types, difficulty_score, stars, rare_analysis,
    tool_version=None
):
    """
    准备上传数据

    Returns:
        dict: 数据字典
    """
    return {
        'book_name': book_name,
        'author': author if author else None,
        'char_types': len(char_counter),
        'char_types_in_1500': len(char_counter) - extra_char_types,
        'char_types_out_1500': extra_char_types,
        'coverage_500': round(coverage_stats[500]['coverage'], 2),
        'coverage_1000': round(coverage_stats[1000]['coverage'], 2),
        'coverage_1500': round(coverage_stats[1500]['coverage'], 2),
        'avg_order_95': round(avg_order_95, 2) if avg_order_95 is not None else None,
        'avg_order_99': round(avg_order_99, 2) if avg_order_99 is not None else None,
        'chars_95': chars_95,
        'chars_99': chars_99,
        'chars_95_in_1500': chars_95_in_ref,
        'chars_95_out_1500': chars_95_out_ref,
        'chars_99_in_1500': chars_99_in_ref,
        'chars_99_out_1500': chars_99_out_ref,
        'difficulty_score': round(difficulty_score, 2),
        'star_level': stars,
        'file_name': selected_file,
        'total_chars': total_chars,
        'rare_char_types': rare_analysis['rare_type_count'],
        'rare_char_ratio': round(rare_analysis['rare_char_ratio'] * 100, 2),
        'tool_version': tool_version
    }


def load_existing_books(conn):
    """
    【批量优化】一次性加载所有已存在的书籍名称

    Args:
        conn: 数据库连接

    Returns:
        dict: {(book_name, author): book_id} 已存在书籍的映射
    """
    try:
        cursor = conn.cursor()
        sql = "SELECT id, book_name, author FROM book_difficulty"
        cursor.execute(sql)
        results = cursor.fetchall()
        cursor.close()

        # 构建映射：(书名, 作者) -> ID
        existing_books = {}
        for book_id, book_name, author in results:
            key = (book_name, author if author else None)
            existing_books[key] = book_id

        return existing_books
    except Exception as e:
        print(f"⚠ 加载已存在书籍列表失败: {e}")
        return {}


def batch_insert_books(conn, data_list):
    """
    【批量优化】批量插入多条书籍记录

    Args:
        conn: 数据库连接
        data_list: 统计数据字典列表

    Returns:
        int: 成功插入的记录数
    """
    if not data_list:
        return 0

    try:
        cursor = conn.cursor()

        sql = """
        INSERT INTO book_difficulty (
            book_name, author, char_types, char_types_in_1500, char_types_out_1500,
            coverage_500, coverage_1000, coverage_1500,
            avg_order_95, avg_order_99,
            chars_95, chars_99,
            chars_95_in_1500, chars_95_out_1500,
            chars_99_in_1500, chars_99_out_1500,
            difficulty_score, star_level,
            file_name, total_chars,
            rare_char_types, rare_char_ratio,
            tool_version
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s
        )
        """

        # 准备批量数据
        values_list = []
        for data in data_list:
            values = (
                data['book_name'], data['author'], data['char_types'],
                data['char_types_in_1500'], data['char_types_out_1500'],
                data['coverage_500'], data['coverage_1000'], data['coverage_1500'],
                data['avg_order_95'], data['avg_order_99'],
                data['chars_95'], data['chars_99'],
                data['chars_95_in_1500'], data['chars_95_out_1500'],
                data['chars_99_in_1500'], data['chars_99_out_1500'],
                data['difficulty_score'], data['star_level'],
                data['file_name'], data['total_chars'],
                data['rare_char_types'], data['rare_char_ratio'],
                data['tool_version']
            )
            values_list.append(values)

        # 批量执行
        cursor.executemany(sql, values_list)
        conn.commit()

        affected_rows = cursor.rowcount
        cursor.close()

        return affected_rows

    except Exception as e:
        print(f"  ✗ 批量插入失败: {e}")
        conn.rollback()
        return 0


def batch_update_books(conn, data_list):
    """
    【批量优化】批量更新多条书籍记录

    Args:
        conn: 数据库连接
        data_list: 统计数据字典列表

    Returns:
        int: 成功更新的记录数
    """
    if not data_list:
        return 0

    try:
        cursor = conn.cursor()

        sql = """
        UPDATE book_difficulty SET
            char_types = %s,
            char_types_in_1500 = %s,
            char_types_out_1500 = %s,
            coverage_500 = %s,
            coverage_1000 = %s,
            coverage_1500 = %s,
            avg_order_95 = %s,
            avg_order_99 = %s,
            chars_95 = %s,
            chars_99 = %s,
            chars_95_in_1500 = %s,
            chars_95_out_1500 = %s,
            chars_99_in_1500 = %s,
            chars_99_out_1500 = %s,
            difficulty_score = %s,
            star_level = %s,
            file_name = %s,
            total_chars = %s,
            rare_char_types = %s,
            rare_char_ratio = %s,
            tool_version = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE book_name = %s AND (author = %s OR (author IS NULL AND %s IS NULL))
        """

        # 准备批量数据
        values_list = []
        for data in data_list:
            values = (
                data['char_types'], data['char_types_in_1500'], data['char_types_out_1500'],
                data['coverage_500'], data['coverage_1000'], data['coverage_1500'],
                data['avg_order_95'], data['avg_order_99'],
                data['chars_95'], data['chars_99'],
                data['chars_95_in_1500'], data['chars_95_out_1500'],
                data['chars_99_in_1500'], data['chars_99_out_1500'],
                data['difficulty_score'], data['star_level'],
                data['file_name'], data['total_chars'],
                data['rare_char_types'], data['rare_char_ratio'],
                data['tool_version'],
                data['book_name'], data['author'], data['author']
            )
            values_list.append(values)

        # 批量执行
        cursor.executemany(sql, values_list)
        conn.commit()

        affected_rows = cursor.rowcount
        cursor.close()

        return affected_rows

    except Exception as e:
        print(f"  ✗ 批量更新失败: {e}")
        conn.rollback()
        return 0


def handle_database_upload(
    selected_file, total_chars, char_counter, coverage_stats,
    avg_order_95, avg_order_99, chars_95, chars_99, chars_95_in_ref, chars_95_out_ref,
    chars_99_in_ref, chars_99_out_ref, extra_char_types, difficulty_score, stars, rare_analysis,
    tool_version=None, batch_mode=False, db_conn=None, db_config=None, existing_books=None
):
    """
    处理数据库上传流程

    Args:
        tool_version: 工具版本号
        batch_mode: 是否批量模式（True=自动处理，False=允许用户确认）
        db_conn: 复用的数据库连接（批量模式用）
        db_config: 数据库配置（批量模式用）
        existing_books: 【批量优化】已存在书籍的缓存 {(book_name, author): book_id}

    Returns:
        批量模式: (success, conn, prepared_data, is_update)
        单文件模式: (success, conn)
    """
    # 加载配置（如果没有传入）
    if db_config is None:
        db_config = load_db_config()
        if not db_config:
            return False, None, None, False if batch_mode else (False, None)

    # 自动检测配置有效性（检查是否仍为模板占位符）
    if not is_db_config_valid(db_config):
        return False, None, None, False if batch_mode else (False, None)

    # 建立数据库连接（如果没有传入）
    if db_conn is None:
        success, db_conn = check_db_connection(db_config)
        if not success:
            return False, None, None, False if batch_mode else (False, None)
        need_close = True  # 标记需要关闭连接
    else:
        need_close = False  # 复用连接，不关闭

    # 从文件名提取书名和作者
    book_name, author = parse_book_info_from_filename(selected_file)

    # 验证书名是否有效
    if not book_name or len(book_name.strip()) == 0:
        if not batch_mode:
            print(f"\n⚠ 无法解析书名，跳过数据库上传")
        ret_conn = db_conn if not need_close else None
        return (False, ret_conn, None, False) if batch_mode else (False, ret_conn)

    # 检查书名中是否包含中文字符
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in book_name)

    # 如果书名没有中文字符
    if not has_chinese:
        if batch_mode:
            # 批量模式：直接跳过（可能是英文书或解析错误）
            ret_conn = db_conn if not need_close else None
            return False, ret_conn, None, False
        else:
            # 单文件模式：提示用户，给予手动输入机会
            print(f"\n⚠ 书名中没有中文字符: {book_name}")
            print("  这可能是英文书或文件名解析错误")
            manual_input = input("  是否手动输入中文书名？(y=是, 其他=跳过): ").strip().lower()
            if manual_input != 'y':
                return False, db_conn if not need_close else None

            # 手动输入书名
            book_name = input("请输入中文书名: ").strip()
            if not book_name or not any('\u4e00' <= char <= '\u9fff' for char in book_name):
                print("书名无效或不包含中文，跳过上传")
                if need_close:
                    db_conn.close()
                return False, None
            author = input("请输入作者（留空跳过）: ").strip() or None

    # 【批量优化】查重：使用缓存或查询数据库
    if batch_mode and existing_books is not None:
        # 批量模式：使用缓存
        book_key = (book_name, author if author else None)
        book_exists = book_key in existing_books
    else:
        # 单文件模式或无缓存：查询数据库
        book_exists = check_book_exists(db_conn, book_name, author)

    if book_exists:
        if batch_mode:
            # 批量模式：自动覆盖更新已存在的记录（静默更新）
            pass  # 继续执行，后面会返回待更新数据
        else:
            # 单文件模式：询问是否覆盖
            print(f"\n⚠ 数据库中已存在: {book_name}" + (f" ({author})" if author else ""))
            overwrite = input("是否覆盖更新？(y=是, n=跳过) [默认:n，直接回车跳过]: ").strip().lower()
            if overwrite == '':
                overwrite = 'n'  # 默认不覆盖
            if overwrite != 'y':
                if need_close:
                    db_conn.close()
                return False, None

    # 单文件模式：显示识别结果，允许修改
    if not batch_mode:
        print("\n" + "=" * 70)
        print("数据库上传")
        print("=" * 70)
        print(f"自动识别结果：")
        print(f"  书名: {book_name}")
        print(f"  作者: {author if author else '(无)'}")

        confirm = input("\n是否使用上述信息？(y=是, n=手动输入, s=跳过): ").strip().lower()

        if confirm == 's':
            if need_close:
                db_conn.close()
            return False, None
        elif confirm == 'n':
            book_name = input("请输入书名: ").strip()
            if not book_name:
                print("书名不能为空，跳过上传")
                if need_close:
                    db_conn.close()
                return False, None
            author = input("请输入作者（留空跳过）: ").strip() or None

            # 再次查重
            book_exists_again = check_book_exists(db_conn, book_name, author)
            if book_exists_again:
                print(f"\n⚠ 数据库中已存在: {book_name}" + (f" ({author})" if author else ""))
                overwrite = input("是否覆盖更新？(y=是, n=跳过) [默认:n，直接回车跳过]: ").strip().lower()
                if overwrite == '':
                    overwrite = 'n'  # 默认不覆盖
                if overwrite != 'y':
                    if need_close:
                        db_conn.close()
                    return False, None
                # 标记需要更新
                book_exists = True

    # 准备数据
    data = prepare_upload_data(
        book_name, author, selected_file, total_chars, char_counter, coverage_stats,
        avg_order_95, avg_order_99, chars_95, chars_99, chars_95_in_ref, chars_95_out_ref,
        chars_99_in_ref, chars_99_out_ref, extra_char_types, difficulty_score, stars, rare_analysis,
        tool_version=tool_version
    )

    # 检查字数是否达到最低要求（300字）
    if total_chars < 300:
        if not batch_mode:
            print(f"\n⚠ 字数过少（{total_chars}字），需要至少300字才能上传数据库")
        ret_conn = None if need_close else db_conn
        if need_close and db_conn:
            db_conn.close()
        return (False, ret_conn, None, False) if batch_mode else (False, ret_conn)

    # 【批量优化】批量模式：只准备数据，不执行SQL
    if batch_mode:
        # 返回：(成功标记, 数据库连接, 准备好的数据, 是否更新)
        return True, db_conn if not need_close else None, data, book_exists

    # 单文件模式：立即执行SQL
    if book_exists:
        success = update_database(db_conn, data)
    else:
        success = upload_to_database(db_conn, data)

    # 关闭连接（如果是自己创建的）
    if need_close:
        db_conn.close()
        return success, None
    else:
        return success, db_conn

