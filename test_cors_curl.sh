#!/bin/bash
# CORS 预检请求测试脚本

echo "========================================"
echo "CORS 预检请求测试"
echo "========================================"
echo ""

# 测试 1: 无效来源（应该被拒绝）
echo "测试 1: 无效来源（应该被拒绝）"
echo "----------------------------------------"
curl -X OPTIONS http://localhost:8000/api/atoms \
  -H "Origin: https://malicious.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" \
  -v 2>&1 | grep -E "Access-Control-Allow-Origin|HTTP/1.1"

echo ""

# 测试 2: 有效来源（应该被允许）
echo "测试 2: 有效来源（应该被允许）"
echo "----------------------------------------"
curl -X OPTIONS http://localhost:8000/api/atoms \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" \
  -v 2>&1 | grep -E "Access-Control-Allow-Origin|HTTP/1.1"

echo ""

# 测试 3: 无 Origin 标头（应该被拒绝）
echo "测试 3: 无 Origin 标头（应该被拒绝）"
echo "----------------------------------------"
curl -X OPTIONS http://localhost:8000/api/atoms \
  -H "Access-Control-Request-Method: GET" \
  -v 2>&1 | grep -E "Access-Control-Allow-Origin|HTTP/1.1"

echo ""

# 测试 4: 实际 GET 请求（带有效来源）
echo "测试 4: 实际 GET 请求（带有效来源）"
echo "----------------------------------------"
curl -X GET http://localhost:8000/api/health \
  -H "Origin: http://localhost:3000" \
  -v 2>&1 | grep -E "Access-Control-Allow-Origin|HTTP/1.1"

echo ""
echo "========================================"
echo "测试完成"
echo "========================================"