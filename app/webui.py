"""
WebUI 仪表板
提供美观的统计数据展示界面
"""
import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

from app.stats import get_stats

logger = logging.getLogger(__name__)

# WebUI 端口
WEBUI_PORT = int(os.getenv("WEBUI_PORT", "8004"))

app = FastAPI(
    title="Content Filter Dashboard",
    description="请求统计仪表板",
    version="1.0.0"
)


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>请求统计仪表板</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --bg-primary: #0f0f1a;
            --bg-secondary: #1a1a2e;
            --bg-card: #16213e;
            --bg-card-hover: #1a2744;
            --accent-primary: #00d4ff;
            --accent-secondary: #7c3aed;
            --accent-success: #10b981;
            --accent-warning: #f59e0b;
            --accent-danger: #ef4444;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-color: rgba(255, 255, 255, 0.1);
            --shadow-glow: 0 0 40px rgba(0, 212, 255, 0.15);
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        /* Animated background */
        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: -1;
            background: 
                radial-gradient(circle at 20% 80%, rgba(124, 58, 237, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(0, 212, 255, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(16, 185, 129, 0.08) 0%, transparent 40%);
            animation: bgPulse 15s ease-in-out infinite;
        }
        
        @keyframes bgPulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(1.05); }
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        /* Header */
        .header {
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem 0;
        }
        
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        }
        
        .header .subtitle {
            color: var(--text-secondary);
            font-size: 1rem;
            font-weight: 400;
        }
        
        .uptime-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            margin-top: 1rem;
            padding: 0.5rem 1rem;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 2rem;
            font-size: 0.875rem;
            color: var(--accent-success);
        }
        
        .uptime-badge::before {
            content: '';
            width: 8px;
            height: 8px;
            background: var(--accent-success);
            border-radius: 50%;
            animation: pulse 2s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.8); }
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1rem;
            padding: 1.75rem;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--card-accent, var(--accent-primary)), transparent);
        }
        
        .stat-card:hover {
            background: var(--bg-card-hover);
            transform: translateY(-4px);
            box-shadow: var(--shadow-glow);
            border-color: rgba(0, 212, 255, 0.3);
        }
        
        .stat-card.primary { --card-accent: var(--accent-primary); }
        .stat-card.success { --card-accent: var(--accent-success); }
        .stat-card.warning { --card-accent: var(--accent-warning); }
        .stat-card.danger { --card-accent: var(--accent-danger); }
        .stat-card.purple { --card-accent: var(--accent-secondary); }
        
        .stat-card .label {
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-secondary);
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .stat-card .label .icon {
            font-size: 1.25rem;
        }
        
        .stat-card .value {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1;
            margin-bottom: 0.5rem;
        }
        
        .stat-card .subtext {
            font-size: 0.8rem;
            color: var(--text-muted);
        }
        
        /* Progress bar for fallback rate */
        .progress-container {
            margin-top: 1rem;
        }
        
        .progress-bar {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
            background: linear-gradient(90deg, var(--accent-success), var(--accent-warning), var(--accent-danger));
            background-size: 200% 100%;
        }
        
        .progress-fill.low { background: var(--accent-success); }
        .progress-fill.medium { background: var(--accent-warning); }
        .progress-fill.high { background: var(--accent-danger); }
        
        /* RPM Section */
        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .section-title::before {
            content: '';
            width: 4px;
            height: 1.25rem;
            background: linear-gradient(180deg, var(--accent-primary), var(--accent-secondary));
            border-radius: 2px;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            margin-top: 3rem;
            padding: 1.5rem;
            color: var(--text-muted);
            font-size: 0.875rem;
        }
        
        .refresh-indicator {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 2rem;
            margin-top: 1rem;
        }
        
        .refresh-dot {
            width: 6px;
            height: 6px;
            background: var(--accent-primary);
            border-radius: 50%;
            animation: blink 1s ease-in-out infinite;
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .header h1 {
                font-size: 1.75rem;
            }
            
            .stat-card .value {
                font-size: 2rem;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    
    <div class="container">
        <header class="header">
            <h1>📊 请求统计仪表板</h1>
            <p class="subtitle">实时监控 API 请求与回退状态</p>
            <div class="uptime-badge">
                运行时间: <span id="uptime">加载中...</span>
            </div>
        </header>
        
        <section>
            <h2 class="section-title">📈 总体统计</h2>
            <div class="stats-grid">
                <div class="stat-card primary">
                    <div class="label"><span class="icon">📨</span> 总请求数</div>
                    <div class="value" id="total-requests">-</div>
                    <div class="subtext">自启动以来的所有请求</div>
                </div>
                
                <div class="stat-card success">
                    <div class="label"><span class="icon">✅</span> 正常处理</div>
                    <div class="value" id="total-normal">-</div>
                    <div class="subtext">成功由正常上游处理</div>
                </div>
                
                <div class="stat-card warning">
                    <div class="label"><span class="icon">🔄</span> 回退请求</div>
                    <div class="value" id="total-fallback">-</div>
                    <div class="subtext">回退到备用上游处理</div>
                </div>
                
                <div class="stat-card danger">
                    <div class="label"><span class="icon">📉</span> 回退率</div>
                    <div class="value" id="fallback-rate">-</div>
                    <div class="subtext">总回退请求百分比</div>
                    <div class="progress-container">
                        <div class="progress-bar">
                            <div class="progress-fill" id="fallback-progress" style="width: 0%"></div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
        
        <section>
            <h2 class="section-title">⚡ 实时 RPM (每分钟请求数)</h2>
            <div class="stats-grid">
                <div class="stat-card purple">
                    <div class="label"><span class="icon">🚀</span> 总 RPM</div>
                    <div class="value" id="rpm-total">-</div>
                    <div class="subtext">过去 60 秒的请求速率</div>
                </div>
                
                <div class="stat-card success">
                    <div class="label"><span class="icon">💚</span> 正常 RPM</div>
                    <div class="value" id="rpm-normal">-</div>
                    <div class="subtext">正常上游请求速率</div>
                </div>
                
                <div class="stat-card warning">
                    <div class="label"><span class="icon">🔶</span> 回退 RPM</div>
                    <div class="value" id="rpm-fallback">-</div>
                    <div class="subtext">回退请求速率</div>
                </div>
                
                <div class="stat-card primary">
                    <div class="label"><span class="icon">📊</span> 窗口回退率</div>
                    <div class="value" id="window-fallback-rate">-</div>
                    <div class="subtext">最近 60 秒的回退率</div>
                </div>
            </div>
        </section>
        
        <footer class="footer">
            <p>Content Filter Middleware Dashboard</p>
            <div class="refresh-indicator">
                <span class="refresh-dot"></span>
                每秒自动刷新
            </div>
        </footer>
    </div>
    
    <script>
        async function fetchStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                updateUI(data);
            } catch (error) {
                console.error('获取统计数据失败:', error);
            }
        }
        
        function updateUI(data) {
            // 更新运行时间
            document.getElementById('uptime').textContent = data.uptime_formatted;
            
            // 更新总体统计
            document.getElementById('total-requests').textContent = formatNumber(data.total_requests);
            document.getElementById('total-normal').textContent = formatNumber(data.total_normal);
            document.getElementById('total-fallback').textContent = formatNumber(data.total_fallback);
            document.getElementById('fallback-rate').textContent = data.fallback_rate + '%';
            
            // 更新回退率进度条
            const progressFill = document.getElementById('fallback-progress');
            progressFill.style.width = Math.min(data.fallback_rate, 100) + '%';
            progressFill.className = 'progress-fill ' + getRateClass(data.fallback_rate);
            
            // 更新 RPM
            document.getElementById('rpm-total').textContent = formatNumber(data.rpm_total);
            document.getElementById('rpm-normal').textContent = formatNumber(data.rpm_normal);
            document.getElementById('rpm-fallback').textContent = formatNumber(data.rpm_fallback);
            document.getElementById('window-fallback-rate').textContent = data.window_fallback_rate + '%';
        }
        
        function formatNumber(num) {
            if (num >= 1000000) {
                return (num / 1000000).toFixed(1) + 'M';
            } else if (num >= 1000) {
                return (num / 1000).toFixed(1) + 'K';
            }
            return num.toString();
        }
        
        function getRateClass(rate) {
            if (rate < 10) return 'low';
            if (rate < 30) return 'medium';
            return 'high';
        }
        
        // 初始加载
        fetchStats();
        
        // 每秒刷新
        setInterval(fetchStats, 1000);
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """返回仪表板 HTML 页面"""
    return DASHBOARD_HTML


@app.get("/api/stats")
async def api_stats():
    """返回统计数据 JSON"""
    stats = get_stats()
    return JSONResponse(content=stats.get_stats())


def run_webui():
    """运行 WebUI 服务器"""
    logger.info(f"WebUI 仪表板启动在端口 {WEBUI_PORT}")
    uvicorn.run(
        "app.webui:app",
        host="0.0.0.0",
        port=WEBUI_PORT,
        log_level="warning"
    )


if __name__ == "__main__":
    run_webui()
