#!/usr/bin/env bash
# 凭据闸门自测：用构造的假凭据检查「该拦的都拦、不该拦的不拦」。
# 假值都是拼出来的，不是任何真实凭据。
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
guard="$(sed -n "s/^guard='\(.*\)'$/\1/p" "$here/scripts/collect-local.sh" | sed "s/'\"'\"'/'/g")"
t="$(mktemp -d)"; trap 'rm -rf "$t"' EXIT; mkdir "$t/hit" "$t/miss"
F="FAKE"; f20="${F}${F}${F}${F}${F}"
hits=(
  "api_key = s""k-test_${f20}1234"
  "令牌 gh""p_${f20}${F}${F}1234"
  "-----BEGIN OPENSSH PRIV""ATE KEY-----"
  "连接串 postgres://admin:Fake""pass123@db.example.com:5432/app"
  "Authorization: Bea""rer abcdef${f20}12345"
  "password: hunter2fake"
  "密码是 Fake1234"
  "口令：\"Fake!2345\""
  "登录时输入密码 \"Fake1234x\""
  "SERVICE_KEY=ey""JhbGciOiJIUzI1Ni${f20}.${F}"
  "授权码：ABCDEFGH12345678"
  "expect 脚本 send \"Fake12345\\r\""
  "slack xo""xb-1234567890-${F}${F}${F}"
  "AK""IA${F}${F}${F}1234"
  "secret: abcdefghijklmnopqrstuv"
)
misses=(
  "密码不要写进代码，存本机钥匙串"
  "排查口令：\`docker logs box | grep cache\`"
  "口令是能读写全部任务数据的凭证，要守隐私铁律"
  "私钥位置在 ~/.keys/ 目录下，内容永远不进 git"
  "验证码样本回传只传题图和作答轨迹"
  "token 用量每天约三十万"
  "官网地址 https://example.com/download"
  "这个接口需要 Bearer 鉴权，具体值在设置页填"
)
i=0; for l in "${hits[@]}";   do i=$((i+1)); printf '%s\n' "$l" > "$t/hit/$i.md";  done
i=0; for l in "${misses[@]}"; do i=$((i+1)); printf '%s\n' "$l" > "$t/miss/$i.md"; done
caught=$( { grep -Eil -- "$guard" "$t"/hit/*.md || true; } | wc -l | tr -d ' ')
false_pos=$( { grep -Eil -- "$guard" "$t"/miss/*.md || true; } | wc -l | tr -d ' ')
echo "该拦 ${#hits[@]}，拦下 ${caught}；不该拦 ${#misses[@]}，误拦 ${false_pos}"
if [ "$caught" -ne "${#hits[@]}" ]; then echo "漏拦："; grep -EiL -- "$guard" "$t"/hit/*.md | xargs cat; exit 1; fi
if [ "$false_pos" -ne 0 ]; then echo "误拦："; grep -Eil -- "$guard" "$t"/miss/*.md | xargs cat; exit 1; fi
echo "通过"
