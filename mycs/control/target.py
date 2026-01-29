from datetime import datetime

from DB.targetdb import delete_agent, get_all_agents


def list_agents_for_display() -> list[dict]:
    """构造前端模板渲染所需的 agent 展示数据。"""
    agents = get_all_agents()
    result = []
    for agent in agents:
        try:
            last_seen = datetime.fromisoformat(agent['last_seen'])
            offline_seconds = (datetime.utcnow() - last_seen).total_seconds()
            status = "online" if offline_seconds < 300 else "offline"
        except Exception:  # noqa: E722
            status = "unknown"
        result.append({
            "id": agent["id"],
            "ip": agent["ip_address"],
            "hostname": agent["hostname"],
            "os": agent["os"],
            "who": agent["who"],
            "arch": agent["arch"],
            "process_name": agent["process_name"],
            "first_seen": datetime.fromisoformat(agent["first_seen"]).strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": datetime.fromisoformat(agent["last_seen"]).strftime("%Y-%m-%d %H:%M:%S"),
            "status": status
        })
    return result


def delete_agent_by_id(agent_id: str) -> bool:
    """封装删除，方便后续扩展权限或其他流程。"""
    return delete_agent(agent_id)
