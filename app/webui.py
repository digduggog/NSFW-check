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
        
        /* History Table */
        .history-section {
            margin-top: 3rem;
        }
        
        .history-table-container {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1rem;
            overflow: hidden;
        }
        
        .history-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .history-table th {
            background: var(--bg-secondary);
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            font-size: 0.875rem;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border-color);
        }
        
        .history-table td {
            padding: 1rem;
            font-size: 0.9rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        .history-table tr {
            transition: background 0.2s ease;
            cursor: pointer;
        }
        
        .history-table tbody tr:hover {
            background: var(--bg-card-hover);
        }
        
        .history-table tr:last-child td {
            border-bottom: none;
        }
        
        .rate-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .rate-badge.low {
            background: rgba(16, 185, 129, 0.2);
            color: var(--accent-success);
        }
        
        .rate-badge.medium {
            background: rgba(245, 158, 11, 0.2);
            color: var(--accent-warning);
        }
        
        .rate-badge.high {
            background: rgba(239, 68, 68, 0.2);
            color: var(--accent-danger);
        }
        
        .view-detail-btn {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            font-size: 0.75rem;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .view-detail-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
        }
        
        /* Chart container */
        .chart-container {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1rem;
            padding: 1.5rem;
            margin-bottom: 2rem;
            height: 300px;
        }
        
        .chart-canvas {
            width: 100%;
            height: 100%;
        }
        
        /* Tabs */
        .tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
        }
        
        .tab {
            padding: 0.75rem 1.5rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.875rem;
        }
        
        .tab:hover {
            background: var(--bg-card-hover);
        }
        
        .tab.active {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            border-color: transparent;
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
            
            .history-table {
                font-size: 0.8rem;
            }
            
            .history-table th,
            .history-table td {
                padding: 0.75rem;
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
            <h2 class="section-title">📈 今日统计</h2>
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
        
        <section class="history-section">
            <h2 class="section-title">📅 近30天历史统计</h2>
            
            <div class="chart-container">
                <canvas id="historyChart" class="chart-canvas"></canvas>
            </div>
            
            <div class="history-table-container">
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>日期</th>
                            <th>总请求</th>
                            <th>正常</th>
                            <th>回退</th>
                            <th>回退率</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody id="history-table-body">
                        <tr>
                            <td colspan="6" style="text-align: center; color: var(--text-muted);">加载中...</td>
                        </tr>
                    </tbody>
                </table>
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
    
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        let historyChart = null;
        
        async function fetchStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                updateUI(data);
            } catch (error) {
                console.error('获取统计数据失败:', error);
            }
        }
        
        async function fetchRecentDays() {
            try {
                const response = await fetch('/api/recent-days?days=30');
                const data = await response.json();
                updateHistoryTable(data);
                updateHistoryChart(data);
            } catch (error) {
                console.error('获取历史数据失败:', error);
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
        
        function updateHistoryTable(data) {
            const tbody = document.getElementById('history-table-body');
            
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">暂无历史数据</td></tr>';
                return;
            }
            
            tbody.innerHTML = data.map(day => `
                <tr onclick="viewDayDetail('${day.date}')">
                    <td><strong>${day.date}</strong></td>
                    <td>${formatNumber(day.total_requests)}</td>
                    <td style="color: var(--accent-success);">${formatNumber(day.total_normal)}</td>
                    <td style="color: var(--accent-warning);">${formatNumber(day.total_fallback)}</td>
                    <td><span class="rate-badge ${getRateClass(day.fallback_rate)}">${day.fallback_rate}%</span></td>
                    <td><button class="view-detail-btn" onclick="event.stopPropagation(); viewDayDetail('${day.date}')">查看详情</button></td>
                </tr>
            `).join('');
        }
        
        function updateHistoryChart(data) {
            const ctx = document.getElementById('historyChart').getContext('2d');
            
            // 反转数据，使最早的日期在左边
            const reversedData = [...data].reverse();
            
            const labels = reversedData.map(d => d.date.substring(5)); // 只显示月-日
            const normalData = reversedData.map(d => d.total_normal);
            const fallbackData = reversedData.map(d => d.total_fallback);
            
            if (historyChart) {
                historyChart.destroy();
            }
            
            historyChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: '正常请求',
                            data: normalData,
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: '回退请求',
                            data: fallbackData,
                            borderColor: '#f59e0b',
                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                            fill: true,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#94a3b8'
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            },
                            ticks: {
                                color: '#64748b'
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            },
                            ticks: {
                                color: '#64748b'
                            }
                        }
                    }
                }
            });
        }
        
        function viewDayDetail(date) {
            window.location.href = '/day/' + date;
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
        fetchRecentDays();
        
        // 每秒刷新实时数据
        setInterval(fetchStats, 1000);
        
        // 每分钟刷新历史数据
        setInterval(fetchRecentDays, 60000);
    </script>
</body>
</html>
"""


DAY_DETAIL_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{date} - 详细统计</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {{
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
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }}
        
        .bg-animation {{
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
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .back-btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            color: var(--text-secondary);
            text-decoration: none;
            transition: all 0.2s;
            margin-bottom: 2rem;
        }}
        
        .back-btn:hover {{
            background: var(--bg-card-hover);
            color: var(--text-primary);
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem 0;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }}
        
        .header .subtitle {{
            color: var(--text-secondary);
            font-size: 1rem;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1rem;
            padding: 1.75rem;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--card-accent, var(--accent-primary)), transparent);
        }}
        
        .stat-card:hover {{
            background: var(--bg-card-hover);
            transform: translateY(-4px);
            box-shadow: var(--shadow-glow);
        }}
        
        .stat-card.primary {{ --card-accent: var(--accent-primary); }}
        .stat-card.success {{ --card-accent: var(--accent-success); }}
        .stat-card.warning {{ --card-accent: var(--accent-warning); }}
        .stat-card.danger {{ --card-accent: var(--accent-danger); }}
        
        .stat-card .label {{
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-secondary);
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .stat-card .value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1;
        }}
        
        .section-title {{
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
            margin: 2rem 0 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .section-title::before {{
            content: '';
            width: 4px;
            height: 1.25rem;
            background: linear-gradient(180deg, var(--accent-primary), var(--accent-secondary));
            border-radius: 2px;
        }}
        
        .chart-container {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1rem;
            padding: 1.5rem;
            height: 350px;
        }}
        
        .hourly-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }}
        
        .hourly-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            padding: 1rem;
            text-align: center;
            transition: all 0.2s;
        }}
        
        .hourly-card:hover {{
            background: var(--bg-card-hover);
        }}
        
        .hourly-card .hour {{
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
        }}
        
        .hourly-card .count {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }}
        
        .hourly-card .breakdown {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }}
        
        .no-data {{
            text-align: center;
            padding: 3rem;
            color: var(--text-muted);
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            
            .header h1 {{
                font-size: 1.75rem;
            }}
            
            .stat-card .value {{
                font-size: 2rem;
            }}
            
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    
    <div class="container">
        <a href="/" class="back-btn">← 返回仪表板</a>
        
        <header class="header">
            <h1>📊 {date}</h1>
            <p class="subtitle">当日详细统计数据</p>
        </header>
        
        <div id="content">
            <div class="no-data">加载中...</div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const date = '{date}';
        
        async function loadDayStats() {{
            try {{
                const response = await fetch('/api/daily/' + date);
                const data = await response.json();
                
                if (data.error) {{
                    document.getElementById('content').innerHTML = '<div class="no-data">😕 ' + data.error + '</div>';
                    return;
                }}
                
                renderContent(data);
            }} catch (error) {{
                console.error('加载数据失败:', error);
                document.getElementById('content').innerHTML = '<div class="no-data">加载失败，请刷新重试</div>';
            }}
        }}
        
        function renderContent(data) {{
            const fallbackRate = data.total_requests > 0 
                ? (data.total_fallback / data.total_requests * 100).toFixed(2) 
                : 0;
            
            let html = `
                <div class="stats-grid">
                    <div class="stat-card primary">
                        <div class="label">📨 总请求数</div>
                        <div class="value">${{formatNumber(data.total_requests)}}</div>
                    </div>
                    <div class="stat-card success">
                        <div class="label">✅ 正常请求</div>
                        <div class="value">${{formatNumber(data.total_normal)}}</div>
                    </div>
                    <div class="stat-card warning">
                        <div class="label">🔄 回退请求</div>
                        <div class="value">${{formatNumber(data.total_fallback)}}</div>
                    </div>
                    <div class="stat-card danger">
                        <div class="label">📉 回退率</div>
                        <div class="value">${{fallbackRate}}%</div>
                    </div>
                </div>
            `;
            
            // 小时统计图表
            if (data.hourly_stats && Object.keys(data.hourly_stats).length > 0) {{
                html += `
                    <h2 class="section-title">⏱️ 小时分布</h2>
                    <div class="chart-container">
                        <canvas id="hourlyChart"></canvas>
                    </div>
                    
                    <h2 class="section-title">📋 小时详情</h2>
                    <div class="hourly-grid">
                `;
                
                // 生成24小时的卡片
                for (let h = 0; h < 24; h++) {{
                    const hour = h.toString().padStart(2, '0');
                    const hourData = data.hourly_stats[hour] || {{ total: 0, normal: 0, fallback: 0 }};
                    html += `
                        <div class="hourly-card">
                            <div class="hour">${{hour}}:00</div>
                            <div class="count">${{hourData.total}}</div>
                            <div class="breakdown">
                                <span style="color: var(--accent-success);">${{hourData.normal}}</span> / 
                                <span style="color: var(--accent-warning);">${{hourData.fallback}}</span>
                            </div>
                        </div>
                    `;
                }}
                
                html += '</div>';
            }} else {{
                html += '<div class="no-data">暂无小时级别统计数据</div>';
            }}
            
            document.getElementById('content').innerHTML = html;
            
            // 渲染图表
            if (data.hourly_stats && Object.keys(data.hourly_stats).length > 0) {{
                renderHourlyChart(data.hourly_stats);
            }}
        }}
        
        function renderHourlyChart(hourlyStats) {{
            const ctx = document.getElementById('hourlyChart').getContext('2d');
            
            const labels = [];
            const normalData = [];
            const fallbackData = [];
            
            for (let h = 0; h < 24; h++) {{
                const hour = h.toString().padStart(2, '0');
                labels.push(hour + ':00');
                const data = hourlyStats[hour] || {{ normal: 0, fallback: 0 }};
                normalData.push(data.normal);
                fallbackData.push(data.fallback);
            }}
            
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: [
                        {{
                            label: '正常请求',
                            data: normalData,
                            backgroundColor: 'rgba(16, 185, 129, 0.8)',
                            borderRadius: 4
                        }},
                        {{
                            label: '回退请求',
                            data: fallbackData,
                            backgroundColor: 'rgba(245, 158, 11, 0.8)',
                            borderRadius: 4
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            labels: {{
                                color: '#94a3b8'
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            stacked: true,
                            grid: {{
                                color: 'rgba(255, 255, 255, 0.05)'
                            }},
                            ticks: {{
                                color: '#64748b'
                            }}
                        }},
                        y: {{
                            stacked: true,
                            grid: {{
                                color: 'rgba(255, 255, 255, 0.05)'
                            }},
                            ticks: {{
                                color: '#64748b'
                            }}
                        }}
                    }}
                }}
            }});
        }}
        
        function formatNumber(num) {{
            if (num >= 1000000) {{
                return (num / 1000000).toFixed(1) + 'M';
            }} else if (num >= 1000) {{
                return (num / 1000).toFixed(1) + 'K';
            }}
            return num.toString();
        }}
        
        loadDayStats();
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """返回仪表板 HTML 页面"""
    return DASHBOARD_HTML


@app.get("/day/{date}", response_class=HTMLResponse)
async def day_detail(date: str):
    """返回指定日期的详情页面"""
    return DAY_DETAIL_HTML.format(date=date)


@app.get("/api/stats")
async def api_stats():
    """返回统计数据 JSON"""
    stats = get_stats()
    return JSONResponse(content=stats.get_stats())


@app.get("/api/daily/{date}")
async def api_daily_stats(date: str):
    """返回指定日期的统计数据"""
    stats = get_stats()
    data = stats.get_daily_stats(date)
    if data is None:
        return JSONResponse(content={"error": f"没有 {date} 的统计数据"})
    return JSONResponse(content=data)


@app.get("/api/recent-days")
async def api_recent_days(days: int = 30):
    """返回近N天的统计概览"""
    stats = get_stats()
    data = stats.get_recent_days_stats(days)
    return JSONResponse(content=data)


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
