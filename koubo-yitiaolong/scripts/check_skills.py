#!/usr/bin/env python3
"""Agent Skills 适配检查（VS Code / GitHub Copilot / 其他读 ~/.agents/skills 的 agent）。

用法:
  python3 check_skills.py                     # 检查本 skill 所在目录里所有 koubo-* 和 whiteboard-diagram、web-page-demo
  python3 check_skills.py --all               # 扫目录里全部 skill（含别人的）：只查会导致加载失败的硬错误，并统计每次对话的固定消耗
  python3 check_skills.py 路径/某skill 路径/另一个   # 只检查指定的
  python3 check_skills.py --root ~/.agents/skills --report 报告.md

检查依据（VS Code 官方文档）:
  - SKILL.md 必须在 skill 目录根，文件名大写
  - frontmatter 必须有 name、description；name 只能小写字母/数字/连字符，≤64，必须和目录名一致，
    不合规会静默加载失败；description ≤1024 字符
  - 启动时只读 name+description，匹配后才读正文，正文里引用到的文件才会读
额度相关（经验标准，不是官方限制）:
  - description 越长，每次对话固定消耗越多；正文越长，触发时消耗越多；代码写在正文里每次都付费
退出码: 有 ❌ 错误 = 1，否则 0。
"""
import argparse, ast, os, re, subprocess, sys

OK_KEYS = {"name", "description", "argument-hint", "user-invocable", "disable-model-invocation",
           "context", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# 只有 Claude 桌面/网页版才有的工具名或写法：别的 agent 里没有，写进 skill 会让它困惑或乱调用
CLAUDE_ONLY = re.compile(r"propose_skills|SendUserFile|device_bash|device_commit|device_stage|AskUserQuestion|"
                         r"TaskCreate|TaskUpdate|ToolSearch|SearchMcpRegistry|SuggestConnectors|mcp__[a-z_-]+__|computer://|"
                         r"/mnt/user-data|/mnt/skills|/sessions/")  # portable-ok
CLAUDE_WORDS = re.compile(r"连入会话|连进会话|桌面端|云端会话|云端环境|在云端|Cowork|Claude 出|Claude 完成|由 Claude")
ABS_PATH = re.compile(r"(?<![\w.~])(/Users/[^\s`'\"）)]+|/home/[^\s`'\"）)]+|/root/[^\s`'\"）)]*|C:\\\\[^\s`'\"]+)")  # portable-ok
SCRIPT_ABS = re.compile(r"(/Users/|/home/|/root/|/mnt/|/sessions/|/home/claude)")  # portable-ok
FALLBACK = re.compile(r"没有|不在|没装|没连|缺|可选|如果有|有.{0,6}时|if available|optional|fallback|找不到|不可用|内置|自己")
OPTIONAL_SKILLS = ["ra-hook", "ra-renhua", "video-progress-studio"]    # 不属于本套、但会被引用的 skill
CODE_BLOCK_MAX = 40


def est_tokens(text):
    """粗估 token：汉字约 0.8，其他字符约 0.28。只用来比较前后变化，不是精确值。"""
    cjk = len(re.findall(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]", text))
    return int(cjk * 0.8 + (len(text) - cjk) * 0.28)


def parse_frontmatter(text):
    """极简 YAML 解析：只认单行 key: value。返回 (dict, 问题列表, 正文)。"""
    issues = []
    if text.startswith("\ufeff"):
        issues.append(("E", "文件开头有 BOM，frontmatter 会解析失败，请存成无 BOM 的 UTF-8"))
        text = text.lstrip("\ufeff")
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not m:
        return {}, issues + [("E", "没有以 --- 开头和结尾的 frontmatter")], text
    fm, body = {}, m.group(2)
    rows = m.group(1).splitlines()
    i = 0
    while i < len(rows):
        ln = rows[i]; i += 1
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        if ln.startswith((" ", "\t")):          # 嵌套映射/续行：属于上一个 key，合法，忽略
            continue
        k, sep, v = ln.partition(":")
        if not sep:
            issues.append(("E", f"frontmatter 行没有冒号：{ln[:30]}"))
            continue
        k, v = k.strip(), v.strip()
        if v in (">", "|", ">-", "|-", ">+", "|+"):       # 块标量：把后面缩进的行收进来
            block = []
            while i < len(rows) and (not rows[i].strip() or rows[i].startswith((" ", "\t"))):
                block.append(rows[i].strip()); i += 1
            v = (" " if v.startswith(">") else "\n").join(x for x in block if x)
            if k == "description":
                issues.append(("W", "description 用了多行写法，不同 agent 解析不一致，建议改成单行"))
            fm[k] = v
            continue
        quoted = len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'"
        if quoted:
            try:
                v = ast.literal_eval(v) if v[0] == '"' and "\\" not in v else v[1:-1]
            except Exception:
                v = v[1:-1]
        elif ": " in v or v.endswith(":") or " #" in v:
            issues.append(("E", f"{k} 的值里有「: 」或「 #」但没加引号，YAML 会解析错，请整个值用双引号括起来"))
        fm[k] = v
    return fm, issues, body


def check_skill(d, strict=True):
    """返回 (info, issues)。issues = [(级别, 说明)]，级别 E/W/I。"""
    name_dir = os.path.basename(os.path.normpath(d))
    issues, info = [], {"dir": name_dir, "desc_tokens": 0, "body_tokens": 0, "body_lines": 0, "desc_len": 0}
    sm = os.path.join(d, "SKILL.md")
    listing = os.listdir(d)          # 用目录列表比对大小写：macOS 文件系统不分大小写，isfile 查不出 skill.md
    if "SKILL.md" not in listing:
        alt = [f for f in listing if f.lower() == "skill.md"]
        issues.append(("E", "找不到 SKILL.md（文件名必须是全大写的 SKILL.md）" + (f"，现在是 {alt[0]}" if alt else "")))
        return info, issues
    raw = open(sm, "rb").read()
    if b"\r\n" in raw:
        issues.append(("W", "文件用了 Windows 换行（CRLF），建议转成 LF"))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        issues.append(("E", "SKILL.md 不是 UTF-8 编码"))
        return info, issues
    fm, fm_issues, body = parse_frontmatter(text)
    issues += fm_issues
    # ---- frontmatter
    name, desc = fm.get("name", ""), fm.get("description", "")
    if not name:
        issues.append(("E", "缺少 name"))
    else:
        if not NAME_RE.match(name) or len(name) > 64:
            issues.append(("E", f"name「{name}」不合规：只能小写字母、数字、连字符，≤64 字符（不合规会静默加载失败）"))
        if name != name_dir:
            issues.append(("E", f"name「{name}」和目录名「{name_dir}」不一致（必须一致，否则静默加载失败）"))
    if not desc:
        issues.append(("E", "缺少 description"))
    else:
        info["desc_len"] = len(desc)
        info["desc_tokens"] = est_tokens(name + desc)
        if len(desc) > 1024:
            issues.append(("E", f"description 有 {len(desc)} 字符，超过 1024 上限"))
        elif strict and len(desc) > 300:
            issues.append(("W", f"description {len(desc)} 字符偏长：每次对话都会固定占用，建议 ≤300"))
        if strict and not re.search(r"使用|触发|说[“\"「]|当.{0,12}时|Use when|use when|when the user", desc):
            issues.append(("W", "description 里没写触发场景（「什么时候用」），agent 可能匹配不上"))
        if re.search(r"[<>]", desc):
            issues.append(("W", "description 里有 < > 字符，部分 agent 的解析会出问题"))
    for k in fm:
        if k not in OK_KEYS and strict:
            issues.append(("W", f"frontmatter 里的 {k} 不是标准字段，VS Code 会忽略"))
    # ---- 正文
    lines = body.splitlines()
    info["body_lines"], info["body_tokens"] = len(lines), est_tokens(body)
    if len(lines) > 500:
        issues.append(("W", f"正文 {len(lines)} 行，超过 500 行（不是加载失败，但每次触发都很费额度），拆到 references/ 里"))
    elif strict and len(lines) > 180:
        issues.append(("W", f"正文 {len(lines)} 行，建议 ≤180 行，细节拆到 references/ 按需读"))
    if strict and info["body_tokens"] > 3500:
        issues.append(("W", f"正文约 {info['body_tokens']} token，触发一次就吃这么多，建议 ≤3500"))
    in_code, run, longest = False, 0, 0
    for ln in lines:
        if ln.strip().startswith("```"):
            in_code = not in_code
            longest = max(longest, run); run = 0
        elif in_code:
            run += 1
    if strict and longest > CODE_BLOCK_MAX:
        issues.append(("W", f"正文里有 {longest} 行的代码块：代码应放 scripts/，正文只写怎么调用（每次触发都会为它付费）"))
    if not strict:                    # --all：别人的 skill 只查“会不会加载失败”，到此为止
        return info, issues
    for m in CLAUDE_ONLY.finditer(text):
        issues.append(("E", f"出现 Claude 专属工具/路径「{m.group(0)}」，别的 agent 里没有"))
        break
    for m in CLAUDE_WORDS.finditer(body):
        issues.append(("W", f"出现 Claude 环境专属的说法「{m.group(0)}」，换成通用说法"))
        break
    for m in ABS_PATH.finditer(text):
        issues.append(("E", f"写死了绝对路径「{m.group(0)[:50]}」，换成 ~/ 或相对路径"))
        break
    # ---- 引用的文件是否存在 / 孤儿文件
    refs = set(re.findall(r"\]\(((?:references|scripts|assets)/[^)#\s]+)\)", text))
    refs |= set(re.findall(r"`((?:references|scripts|assets)/[^`\s*]+?)`", text))
    for r in sorted(refs):
        if any(c in r for c in "<>{}$"):
            continue
        if not os.path.exists(os.path.join(d, r)):
            issues.append(("E", f"正文引用了不存在的文件 {r}"))
    for sub in ("references", "scripts", "assets"):
        p = os.path.join(d, sub)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            if f.startswith(".") or f == "__pycache__" or f.endswith((".pyc",)):
                continue
            rel = f"{sub}/{f}"
            if not any(rel == r or r.startswith(rel) or rel.startswith(r.rstrip("/")) for r in refs) and f not in text:
                issues.append(("W", f"{rel} 没有在 SKILL.md 里提到，agent 不会知道它存在（孤儿文件）"))
    # ---- 脚本
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in ("__pycache__", "node_modules", ".git")]
        for f in files:
            p = os.path.join(root, f); rel = os.path.relpath(p, d)
            if f in (".DS_Store",) or f.endswith(".pyc"):
                issues.append(("W", f"{rel} 是垃圾文件，请删除"))
            elif f.endswith(".py"):
                try:
                    compile(open(p, encoding="utf-8").read(), p, "exec")      # 只检查语法，不生成 .pyc
                except (SyntaxError, ValueError) as e:
                    issues.append(("E", f"{rel} 语法错误：{str(e)[:80]}"))
                    continue
                for i, ln in enumerate(open(p, encoding="utf-8", errors="ignore"), 1):
                    if SCRIPT_ABS.search(ln) and "portable-ok" not in ln and not ln.strip().startswith("#"):
                        issues.append(("E", f"{rel}:{i} 写死了本机/云端路径：{ln.strip()[:60]}"))
                        break
            elif f.endswith(".sh"):
                r = subprocess.run(["bash", "-n", p], capture_output=True, text=True)
                if r.returncode:
                    issues.append(("E", f"{rel} 语法错误：{r.stderr.strip()[:80]}"))
            elif f.endswith(".json"):
                try:
                    import json; json.load(open(p, encoding="utf-8"))
                except Exception as e:
                    issues.append(("E", f"{rel} 不是合法 JSON：{e}"))
            if os.path.getsize(p) > 3_000_000 and strict:
                issues.append(("W", f"{rel} 有 {os.path.getsize(p)//1_000_000}MB，字体/大素材别放进 skill，改成下载脚本"))
    return info, issues


def cross_refs(dirs, all_names):
    """别的 skill 被点名时，要么已安装，要么这一行写了没有就怎么办。"""
    out = []
    for d in dirs:
        sm = os.path.join(d, "SKILL.md")
        if not os.path.isfile(sm):
            continue
        for ln in open(sm, encoding="utf-8").read().splitlines():
            for s in OPTIONAL_SKILLS:
                if s in ln and s not in all_names and not FALLBACK.search(ln):
                    out.append((os.path.basename(d), f"提到 {s} 但它没安装，且这一行没写「没有就怎么办」：{ln.strip()[:50]}"))
    return out


def main():
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # …/skills
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--root", default=here, help="skill 所在目录（默认：本 skill 的上一级）")
    ap.add_argument("--all", action="store_true", help="检查目录里全部 skill，只报硬错误")
    ap.add_argument("--report", help="把结果另存成 markdown")
    ap.add_argument("-q", "--quiet", action="store_true", help="只显示 ❌ 错误和汇总")
    A = ap.parse_args()
    root = os.path.expanduser(A.root)
    all_dirs = sorted(os.path.join(root, x) for x in os.listdir(root)
                      if os.path.isdir(os.path.join(root, x)) and not x.startswith("."))
    all_dirs = [d for d in all_dirs if any(f.lower() == "skill.md" for f in os.listdir(d)) or os.path.basename(d).startswith(("koubo", "whiteboard", "web-page"))]
    mine = ("koubo-", "whiteboard-diagram", "web-page-demo")
    if A.paths:
        dirs = [os.path.expanduser(p) for p in A.paths]
    elif A.all:
        dirs = all_dirs
    else:
        dirs = [d for d in all_dirs if os.path.basename(d).startswith(mine)]
    strict = not A.all
    names = {os.path.basename(d) for d in all_dirs}
    rows, n_err, n_warn = [], 0, 0
    lines = []
    for d in dirs:
        info, iss = check_skill(d, strict)
        e = [m for l, m in iss if l == "E"]; w = [m for l, m in iss if l == "W"]
        n_err += len(e); n_warn += len(w)
        rows.append((info, len(e), len(w)))
        if iss:
            lines.append(f"\n{info['dir']}")
            for l, m in sorted(iss, key=lambda x: "EWI".index(x[0])):
                if A.quiet and l != "E":
                    continue
                lines.append(f"  {'❌' if l == 'E' else '⚠️ '} {m}")
    for who, m in cross_refs(dirs, names):
        lines.append(f"\n{who}\n  ⚠️  {m}"); n_warn += 1
    tot_desc = sum(r[0]["desc_tokens"] for r in rows)
    head = [f"检查目录：{root}", f"{'skill':26s}{'错误':>4s}{'警告':>4s}{'描述≈tok':>10s}{'正文≈tok':>10s}{'正文行':>7s}",
            "-" * 61]
    for info, e, w in rows:
        flag = "✅" if not e and not w else ("❌" if e else "⚠️")
        head.append(f"{info['dir'][:25]:26s}{e:>4d}{w:>4d}{info['desc_tokens']:>10d}{info['body_tokens']:>10d}{info['body_lines']:>7d}  {flag}")
    head += ["-" * 61, f"共 {len(rows)} 个 skill｜❌ {n_err}｜⚠️ {n_warn}｜"
             f"每次对话固定消耗（所有描述合计）≈ {tot_desc} token｜单个触发时再加正文"]
    if A.all and len(rows) > 8:
        top = sorted(rows, key=lambda r: -r[0]["desc_tokens"])[:5]
        head.append("描述最占地方的 5 个：" + "、".join(f"{r[0]['dir']}（≈{r[0]['desc_tokens']}）" for r in top))
    out = "\n".join(head + lines)
    print(out)
    if A.report:
        open(os.path.expanduser(A.report), "w", encoding="utf-8").write("```\n" + out + "\n```\n")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
