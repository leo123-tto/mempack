#!/usr/bin/env python3
"""mempack · 拆条核对：把「整理记忆」第 2、5 步里能交给程序的检查做掉。

对 facts/ 里的每个拆条文件：
  1. 原话是否能在原件里逐字搜到（比较时忽略空白）；
  2. 原件的每一节有没有被拆到——列出一条事实都没有的节，供你在原件清单里交代或回去补拆；
  3. 原话里带「他 / 她」的事实——逐条核对指的是不是主人；
  4. 随机抽若干条，供你回原件看「内容」有没有比原话多说、说反；
  5. 文件开头有没有总条数、末尾有没有结束标记。

只输出编号、文件名和行号，不输出记忆内容。结果同时写进 run/拆条核对.md（带 --source 时是 run/拆条核对-<来源>.md）。

用法：python3 scripts/check-facts.py [记忆文件夹] [--source 来源-日期] [--sample 15]
      记忆文件夹不写就用环境变量 MEMORY_HOME，再没有就是 ~/mempack-data。
退出码：有原话搜不到、或拆条文件没写完，返回 1；否则 0。
"""
import hashlib, os, random, re, sys

END_MARK = "—— 完 ——"
OWNER = "主人"  # 这个来源的原件在 rulings/，不在 originals/

def norm(s): return re.sub(r"\s+", "", s or "")

def parse_facts(path):
    """每条事实一行：- 编号｜书架｜槽位｜日期｜说法来源｜易变｜内容｜「原话」"""
    facts, declared, ended = [], None, False
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        m = re.match(r"^总条数[:：]\s*(\d+)", line)
        if m: declared = int(m.group(1))
        if line.strip() == END_MARK: ended = True
        if not line.startswith("- ") or "｜" not in line: continue
        parts = line[2:].split("｜")
        if len(parts) < 8: continue
        quote = parts[-1].strip()
        quote = quote[1:-1] if quote.startswith("「") and quote.endswith("」") else quote
        facts.append({"id": parts[0].strip(), "shelf": parts[1].strip(), "quote": quote})
    return facts, declared, ended

def original_files(home, source):
    if source.startswith(OWNER):
        # 主人-2026-10-02-第二批 → rulings/2026-10-02-第二批.md；找不到对应文件才看整个 rulings/
        one = os.path.join(home, "rulings", source[len(OWNER):].lstrip("-") + ".md")
        root = one if os.path.isfile(one) else os.path.join(home, "rulings")
    else:
        root = os.path.join(home, "originals", source)
    if os.path.isfile(root): return [root], os.path.dirname(root)
    out = []
    for d, _, names in os.walk(root):
        out += [os.path.join(d, n) for n in sorted(names) if not n.startswith(".")]
    return sorted(out), root

def sections(path):
    """按原件自己的标题分节；没有标题的文件按空行分段。返回 [(节名, 起始行号, [(行号, 正文行)])]"""
    try: lines = open(path, encoding="utf-8").read().split("\n")
    except (UnicodeDecodeError, OSError): return []
    has_head = any(re.match(r"^#{1,6}\s", l) for l in lines)
    out, cur, in_yaml = [], ["（开头）", 1, []], False
    for i, l in enumerate(lines, 1):
        if l.strip() == "---" and i <= 40 and (i == 1 or in_yaml):
            in_yaml = not in_yaml; continue
        if in_yaml: continue
        if has_head and re.match(r"^#{1,6}\s", l):
            out.append(cur); cur = [l.strip("# ").strip(), i, []]; continue
        if not has_head and not l.strip():
            if cur[2]: out.append(cur); cur = [f"第 {i + 1} 行起的一段", i + 1, []]
            continue
        if len(norm(l)) >= 8: cur[2].append((i, l))
    out.append(cur)
    return [s for s in out if s[2]]

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = {sys.argv[i]: sys.argv[i + 1] for i in range(1, len(sys.argv) - 1) if sys.argv[i].startswith("--")}
    home = os.path.expanduser(args[0] if args else os.environ.get("MEMORY_HOME", "~/mempack-data"))
    n_sample = int(opt.get("--sample", "15"))
    fdir = os.path.join(home, "facts")
    names = sorted(n for n in os.listdir(fdir) if n.endswith(".md")) if os.path.isdir(fdir) else []
    if "--source" in opt: names = [n for n in names if n[:-3] == opt["--source"]]
    if not names: sys.exit("facts/ 里没有要核对的拆条文件")
    report, bad = ["# 拆条核对\n"], False
    for name in names:
        source = name[:-3]
        facts, declared, ended = parse_facts(os.path.join(fdir, name))
        files, root = original_files(home, source)
        report.append(f"\n## {source}\n")
        if not files:
            report.append(f"- 找不到原件（应在 {os.path.relpath(root, home)}）。\n"); bad = True; continue
        texts = {}
        for p in files:
            try: texts[p] = norm(open(p, encoding="utf-8").read())
            except (UnicodeDecodeError, OSError): pass
        quotes = [norm(f["quote"]) for f in facts]
        # 1 原话
        missing = [f["id"] for f, q in zip(facts, quotes) if not q or not any(q in t for t in texts.values())]
        report.append(f"- 事实 {len(facts)} 条；原话在原件里搜不到的 {len(missing)} 条" + (f"：{'、'.join(missing)}" if missing else "") + "\n")
        bad |= bool(missing)
        # 5 文件完整
        if declared is None: report.append("- 文件开头没有「总条数：N」一行。\n")
        elif declared != len(facts): report.append(f"- 开头写的总条数 {declared} 与实际 {len(facts)} 不符。\n")
        if not ended: report.append(f"- 文件末尾没有「{END_MARK}」：这份拆条可能只写了一半。\n"); bad = True
        # 2 逐节覆盖
        # 原件只有一两个文件的，按节看；有很多页的，按页看（一页里只要有一条被引到就不算空）
        by_page = len(files) > 3
        total = covered = 0; empty = []
        for p in files:
            rel = os.path.relpath(p, root) if os.path.isdir(root) else os.path.basename(p)
            page_total = page_hit = 0
            for head, start, body in sections(p):
                hit = sum(1 for _, l in body if any(q and q in norm(l) for q in quotes))
                page_total += len(body); page_hit += hit
                if hit == 0 and not by_page: empty.append(f"{rel}:{start}「{head[:30]}」（{len(body)} 行）")
            total += page_total; covered += page_hit
            if by_page and page_total and page_hit == 0: empty.append(f"{rel}（{page_total} 行）")
        pct = f"{100 * covered / total:.0f}%" if total else "—"
        unit = "页" if by_page else "节"
        report.append(f"- 原件正文 {total} 行，至少被一条原话引到的 {covered} 行（{pct}）。这个比例低不等于漏拆（同一件事只记一次），要看的是下面的空{unit}。\n")
        report.append(f"- 一条事实都没引到的{unit} {len(empty)} 个" + (f"，每一个都要在原件清单里写明原因，或回去补拆：\n" + "".join(f"  - {e}\n" for e in empty) if empty else "。\n"))
        # 3 第三人称
        pron = [f["id"] for f in facts if re.search(r"[他她]", f["quote"])]
        report.append(f"- 原话里带「他 / 她」的 {len(pron)} 条，逐条核对指的是不是主人" + (f"：{'、'.join(pron)}" if pron else "") + "\n")
        # 4 反向抽查
        rnd = random.Random(int(hashlib.md5(source.encode()).hexdigest(), 16))
        pick = sorted(rnd.sample([f["id"] for f in facts], min(n_sample, len(facts))))
        report.append(f"- 反向抽查 {len(pick)} 条（回原件看「内容」有没有比原话多说、说反、把话改温和了）：{'、'.join(pick)}\n")
    text = "".join(report)
    os.makedirs(os.path.join(home, "run"), exist_ok=True)
    out_name = f"拆条核对-{opt['--source']}.md" if "--source" in opt else "拆条核对.md"
    open(os.path.join(home, "run", out_name), "w", encoding="utf-8").write(text)
    print(text)
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
