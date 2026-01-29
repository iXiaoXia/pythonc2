# db.py
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional


DB_PATH = 'teamserver.db'



def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS agents
                   (
                       id
                       TEXT
                       PRIMARY
                       KEY,
                       ip_address
                       TEXT
                       NOT
                       NULL,
                       hostname
                       TEXT,
                       os
                       TEXT,
                       who
                       TEXT, -- 新增：当前用户
                       arch
                       TEXT, -- 新增：CPU 架构 (x86/x64/arm64)
                       process_name
                       TEXT, -- 新增：进程名
                       first_seen
                       TIMESTAMP
                       NOT
                       NULL,
                       last_seen
                       TIMESTAMP
                       NOT
                       NULL
                   )
                   ''')

    conn.commit()
    conn.close()


def register_agent(
        agent_id: str,
        ip: str,
        hostname: str = None,
        os: str = None,
        who: str = None,
        arch: str = None,
        process_name: str = None
):
    """注册或更新主机信息（支持新字段）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute('''
        INSERT OR REPLACE INTO agents 
        (id, ip_address, hostname, os, who, arch, process_name, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?, 
            COALESCE((SELECT first_seen FROM agents WHERE id = ?), ?),
            ?
        )
    ''', (
        agent_id, ip,
        hostname or 'Unknown',
        os or 'Unknown',
        who or 'Unknown',
        arch or 'Unknown',
        process_name or 'Unknown',
        agent_id, now, now
    ))

    conn.commit()
    conn.close()


def get_all_agents():
    """获取所有主机信息"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM agents ORDER BY last_seen DESC')
    agents = cursor.fetchall()
    conn.close()
    return agents


def delete_agent(agent_id: str) -> bool:
    """删除指定 agent，返回是否有记录被移除"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM agents WHERE id = ?', (agent_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0











# DB/targetdb.py
def init_listeners_table():
    """初始化监听器表（带唯一约束）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 先创建表（如果不存在）
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS listeners
                   (
                       name
                       TEXT
                       PRIMARY
                       KEY,
                       listener_type
                       TEXT
                       NOT
                       NULL,
                       port
                       INTEGER
                       NOT
                       NULL,
                       is_running
                       INTEGER
                       NOT
                       NULL
                       DEFAULT
                       0,
                       url_path
                       TEXT,
                       domain
                       TEXT
                   )
                   ''')

    # 添加唯一索引（SQLite 支持部分索引）
    # 注意：url_path 可为 NULL，NULL 不参与唯一性检查（符合需求）
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_listeners_port ON listeners (port)')
    cursor.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_listeners_url ON listeners (url_path) WHERE url_path IS NOT NULL')

    conn.commit()
    conn.close()


def get_all_listeners():
    """获取所有监听器"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM listeners ORDER BY name')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_listener(
        name: str,
        listener_type: str,
        port: int,
        url_path: Optional[str] = None,  # 允许 None
        domain: Optional[str] = None
) -> None:
    _validate_listener_params(name, listener_type, port, url_path, domain)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        if listener_type == "https":
            cursor.execute('''
                           INSERT INTO listeners (name, listener_type, port, is_running, domain, url_path)
                           VALUES (?, ?, ?, 0, ?, ?)
                           ''', (name, listener_type, port, domain, url_path))
        else:
            cursor.execute('''
                           INSERT INTO listeners (name, listener_type, port, is_running, url_path)
                           VALUES (?, ?, ?, 0, ?)
                           ''', (name, listener_type, port, url_path))
        conn.commit()
    except sqlite3.IntegrityError as e:
        if "idx_listeners_port" in str(e):
            raise ValueError("端口已被占用")
        elif "idx_listeners_url" in str(e):
            raise ValueError("URL 路径已被使用")
        else:
            raise ValueError("监听器名称已存在")
    finally:
        conn.close()


def update_listener(
        name: str,
        listener_type: str,
        port: int,
        url_path: Optional[str] = None,
        domain: Optional[str] = None
) -> None:
    _validate_listener_params(name, listener_type, port, url_path, domain, for_update=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        if listener_type == "https":
            cursor.execute('''
                           UPDATE listeners
                           SET listener_type     = ?,
                               port     = ?,
                               domain   = ?,
                               url_path = ?
                           WHERE name = ?
                           ''', (listener_type, port, domain, url_path, name))
        else:
            cursor.execute('''
                           UPDATE listeners
                           SET type     = ?,
                               port     = ?,
                               domain   = NULL,
                               url_path = ?
                           WHERE name = ?
                           ''', (listener_type, port, url_path, name))
        conn.commit()

        # 检查是否因唯一约束失败（SQLite UPDATE 不抛 IntegrityError，需手动查）
        if cursor.rowcount == 0:
            raise ValueError("监听器不存在")
    except sqlite3.IntegrityError as e:
        if "idx_listeners_port" in str(e):
            raise ValueError("端口已被占用")
        elif "idx_listeners_url" in str(e):
            raise ValueError("URL 路径已被使用")
        else:
            raise
    finally:
        conn.close()


def _validate_listener_params(name: str, listener_type: str, port: int, url_path: Optional[str], domain: Optional[str],
                              for_update: bool = False):

    """统一参数校验"""
    if not name or not listener_type:
        print("名称和类型不能为空")
        raise ValueError("名称和类型不能为空")
    if listener_type not in ("http", "https"):
        print("仅支持 http/https 类型")
        raise ValueError("仅支持 http/https 类型")
    if not (1 <= port <= 65535):
        print("端口必须在 1-65535 范围内")
        raise ValueError("端口必须在 1-65535 范围内")

    # 处理 url_path
    if url_path is not None:
        url_path = url_path.strip()
        if url_path == "":
            url_path = None  # 视为空

    if url_path is not None:
        if not is_url_path_valid(url_path):
            print("端口必须在 1-65535 范围内")
            raise ValueError("URL 路径不能为 '/'，不能与系统路由冲突，且必须是合法路径")

    # HTTPS 必须有 domain
    if listener_type == "https" and (not domain or not domain.strip()):
        print("HTTPS 监听器必须指定域名")
        raise ValueError("HTTPS 监听器必须指定域名")

def is_url_path_valid(url_path: str) -> bool:
    """检查 url_path 是否合法：
    - 不能是 None 或空（调用方处理）
    - 不能是 '/'
    - 不能以 // 开头或结尾
    - 不能与系统保留路由冲突
    """
    if not url_path or url_path == '/':
        return False

    # 规范化：确保以 / 开头，不以 / 结尾（除根外）
    if not url_path.startswith('/'):
        url_path = '/' + url_path
    if url_path.endswith('/') and url_path != '/':
        url_path = url_path.rstrip('/')


    # 简单路径合法性（可扩展）
    if '..' in url_path or ' ' in url_path:
        return False

    return True

