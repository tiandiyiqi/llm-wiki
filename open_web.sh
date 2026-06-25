#!/bin/bash
# 启动 llm-wiki 服务并打开浏览器

echo "============================================================"
echo "llm-wiki Web 服务启动器"
echo "============================================================"
echo ""

# 检查服务是否已运行
if lsof -i :8000 >/dev/null 2>&1; then
    echo "✅ 服务已在运行（端口 8000）"
else
    echo "启动服务..."
    source .venv/bin/activate
    python start_server.py --host localhost --port 8000 --kb knowledge-bases &
    sleep 3
    echo "✅ 服务已启动"
fi

echo ""
echo "访问地址："
echo "  主页:      http://localhost:8000/views/index.html"
echo "  登录:      http://localhost:8000/views/login.html"
echo "  知识库:    http://localhost:8000/views/admin/kb-management.html"
echo "  图像库:    http://localhost:8000/views/media/gallery.html"
echo "  搜索:      http://localhost:8000/views/search/results.html"
echo ""
echo "API 端点："
echo "  健康检查:  http://localhost:8000/api/health"
echo "  状态:      http://localhost:8000/api/status"
echo ""
echo "============================================================"
echo ""

# 打开浏览器
open http://localhost:8000/views/index.html

echo "浏览器已打开"
echo ""
echo "按 Ctrl+C 停止服务（如果需要）"