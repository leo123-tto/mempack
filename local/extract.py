#!/usr/bin/env python3
"""记忆行李箱 · 本地模型拆条（实验）

把一份记忆导出文件拆成小事实，交给一个 OpenAI 兼容接口上的模型去做，
程序负责分段、校验和落盘：模型只出结构化结果，原话对不上原文的条目由程序降为「存疑」。
槽位词表（输出目录下的 槽位词表.txt）跨来源累积。设 MEMORY_USE_VOCAB=1 时，拆第二家会把第一家用过的
槽位写法带进提示词。默认不带：试过一次，带上以后只有一成多的条目沿用了旧写法，而那一次
14 段里有 5 段输出被截断（那次换了一份更大的原件，不能断定就是词表造成的）。

用法：
  MEMORY_LLM_URL=http://127.0.0.1:8000/v1 MEMORY_LLM_MODEL=<模型名> MEMORY_LLM_KEY=<可选> \
    python3 local/extract.py <导出文件.md> <来源名> <输出目录>
"""
import json, os, re, sys, time, urllib.request

SHELVES = "10 我是谁｜20 在做的事｜30 懂什么不懂什么｜40 线上资产与设备｜50 用的 AI 与工具｜60 偏好与规矩｜70 人与机构｜80 生活"
SYSTEM = f"""你在帮一个人整理某个 AI 对他的记忆。我给你这份记忆里的一段原文，请把它拆成一条条「小事实」。
小事实 = 一句能单独判真假的话。一行里有几件事就拆开。只拆原文里有的，不要补充、不要推测、不要评价。
跳过：密码、密钥、令牌、证件号、银行卡号。
只输出一个 JSON 数组，不要任何别的文字。数组里每个对象有这些键：
- "content"：一句话，用第三人称写主人（「他……」）
- "shelf"：归到哪个书架，只能是下面之一的编号：{SHELVES}
- "slot"：这句话回答的是哪个问题，写成「主题/对象/属性」的短语，例如「订阅/某产品/档位」。我会给你一份「已有的槽位」，回答的是同一个问题就原样沿用已有的写法，确实没有才新起
- "date"：原文里这条的日期，YYYY-MM-DD；没有写「未知」
- "said_by"：只能是 亲口 / 推断 / 读文档所得 / 调研所得 / 导入 / 未标注 之一，照原文的标注；原文没标就写 未标注
- "quote"：从原文里逐字摘的一小段，不超过 60 个字，必须和原文一字不差
- "volatile"：true 或 false，版本号、人数、余额、进度这类几天就变的为 true
这一段没有可拆的内容就输出 []。"""

def chunks(text, limit=int(os.environ.get("MEMORY_CHUNK_CHARS", "2500"))):
    """按 Markdown 标题分段；一段太长再按行切。"""
    parts, cur, head = [], [], ""
    for line in text.splitlines():
        if re.match(r"^#{1,6}\s", line) and cur:
            parts.append((head, "\n".join(cur))); cur = []
        if re.match(r"^#{1,6}\s", line):
            head = line.strip("# ").strip()
        cur.append(line)
    if cur: parts.append((head, "\n".join(cur)))
    out = []
    for head, body in parts:
        if not body.strip(): continue
        while len(body) > limit:
            cut = body.rfind("\n", 0, limit)
            cut = cut if cut > limit // 2 else limit
            out.append((head, body[:cut])); body = body[cut:]
        out.append((head, body))
    return out

def vocab_text(vocab, limit=int(os.environ.get("MEMORY_VOCAB_CHARS", "6000"))):
    """已有槽位拼成提示词里的一段；太长就只留最近用过的。"""
    out, n = [], 0
    for slot in reversed(list(vocab)):
        n += len(slot) + 1
        if n > limit: break
        out.append(slot)
    return "\n".join(reversed(out)) or "（还没有）"

def ask(url, model, key, user):
    body = {"model": model, "temperature": 0.1, "max_tokens": int(os.environ.get("MEMORY_MAX_TOKENS", "12000")),
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}
    if os.environ.get("MEMORY_LLM_EFFORT"): body["reasoning_effort"] = os.environ["MEMORY_LLM_EFFORT"]
    req = urllib.request.Request(url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + key} if key else {})})
    with urllib.request.urlopen(req, timeout=900) as r:
        c = json.load(r)["choices"][0]
        return (c["message"].get("content") or ""), c.get("finish_reason")

def parse(raw):
    m = re.search(r"\[.*\]", raw, re.S)
    if not m: return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, list) else None
    except Exception:
        return None

def norm(s): return re.sub(r"\s+", "", s or "")

def main():
    if len(sys.argv) != 4: sys.exit(__doc__)
    path, source, outdir = sys.argv[1:]
    url, model, key = os.environ["MEMORY_LLM_URL"], os.environ["MEMORY_LLM_MODEL"], os.environ.get("MEMORY_LLM_KEY", "")
    text = open(path, encoding="utf-8").read()
    os.makedirs(outdir, exist_ok=True)
    vocab_path = os.path.join(outdir, "槽位词表.txt")
    vocab = dict.fromkeys(l.strip() for l in open(vocab_path, encoding="utf-8") if l.strip()) if os.path.exists(vocab_path) else {}
    known, reused, per_chunk = set(vocab), 0, []
    fails, total_chars, done_chars = [], 0, 0
    facts, stat = [], {"chunks": 0, "json_fail": 0, "facts": 0, "quote_ok": 0, "quote_bad": 0, "bad_shelf": 0, "seconds": 0}
    t0 = time.time()
    for idx, (head, body) in enumerate(chunks(text), 1):
        stat["chunks"] += 1; total_chars += len(body)
        data, why = None, []
        for attempt in (1, 2):
            raw, fin = ask(url, model, key, (f"已有的槽位：\n{vocab_text(vocab)}\n\n" if os.environ.get("MEMORY_USE_VOCAB") else "") + f"原文所在的小节：{head or '（无标题）'}\n\n原文：\n{body}")
            data = parse(raw)
            if data is not None: break
            why.append({"finish_reason": fin, "reply_chars": len(raw)})
        if data is None:
            stat["json_fail"] += 1
            fails.append({"chunk": idx, "section": head, "chars": len(body), "attempts": why})
            per_chunk.append({"chunk": idx, "section": head, "chars": len(body), "facts": None}); continue
        done_chars += len(body); n_before = len(facts)
        for f in data:
            if not isinstance(f, dict) or not f.get("content"): continue
            ok = bool(f.get("quote")) and norm(f["quote"]) in norm(body)
            f["quote_found"] = ok; f["section"] = head; f["source"] = source; f["chunk"] = idx
            slot = str(f.get("slot") or "").strip()
            if slot:
                if slot in known: reused += 1
                vocab.pop(slot, None); vocab[slot] = None  # 挪到最后，算「最近用过」
            stat["quote_ok" if ok else "quote_bad"] += 1
            if not re.match(r"^(10|20|30|40|50|60|70|80)", str(f.get("shelf", ""))): stat["bad_shelf"] += 1
            facts.append(f)
        per_chunk.append({"chunk": idx, "section": head, "chars": len(body), "facts": len(facts) - n_before})
    stat["facts"] = len(facts); stat["seconds"] = round(time.time() - t0)
    stat["coverage"] = round(done_chars / total_chars, 3) if total_chars else 0  # 成功处理的原文占比；不到 1 就是有整段丢了
    stat["slots_distinct"] = len({str(f.get("slot")) for f in facts})
    stat["slots_reused_from_vocab"] = reused  # 用了开工前词表里已有写法的条数；跨来源能不能对上账看这个
    stat["empty_chunks"] = [c["chunk"] for c in per_chunk if c["facts"] == 0]  # 有字却一条没拆出来的段，要人看一眼
    with open(vocab_path, "w", encoding="utf-8") as w:
        w.write("\n".join(vocab) + "\n")
    with open(os.path.join(outdir, f"{source}.facts.jsonl"), "w", encoding="utf-8") as w:
        for f in facts: w.write(json.dumps(f, ensure_ascii=False) + "\n")
    with open(os.path.join(outdir, f"{source}.stat.json"), "w", encoding="utf-8") as w:
        json.dump({"model": model, **stat, "failed_chunks": fails, "per_chunk": per_chunk}, w, ensure_ascii=False, indent=1)
    print(json.dumps({"model": model, **stat}, ensure_ascii=False))

if __name__ == "__main__":
    main()
