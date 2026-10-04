#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic 子仓库版本清单 TUI (repo-versions)

- 展示 semantic 工程全部子仓库清单: 配置 ref(清单) / 当前 ref(工作区实际) / 漂移标记
- 每个仓库可输入或从远端分支/Tag 列表选择确定的 branch / tag
- 保存为 repo-versions.json 持久化, 下次启动自动加载
- c/C 一键把工作区各仓库 checkout 到清单 ref (支持中间版本本地测试)
- a 记录(采纳)当前各仓库 HEAD 为清单 (稳定后随 quick-start 提交/打 tag 即版本锁定)
- semantic_installer.py 的 2.2 步骤优先读取本清单构建, 不再依赖硬编码分支

用法:
    python3 repo_versions.py [--config repo-versions.json] [--semantic $SEMANTIC]
    python3 repo_versions.py --freeze v0.5.0 [--semantic $SEMANTIC]   # 生成发布快照
"""

import argparse
import curses
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# 与 semantic_installer.REPOS 保持一致: (本地目录, 默认分支; None=main 不切)
REPOS = [
    ("semantic-framework", "feature/robot-ability-binding"),
    ("semantic-web", "feature/v050-device-workbench"),
    ("semantic-docs", "feature/v050-robot-runtime-docs"),
    ("semantic-ability/r1pro-ability", "feature/r1pro-seven-abilities"),
    ("semantic-robotsdk/robot-sdk", "feature/v040-robot-sdk-core"),
    ("semantic-skill/robot-skill", "feature/robot-skill-skeleton"),
    ("semantic-simulation/mujoco-runtime", "feature/v060-r1pro-tote-gripper-runtime"),
    ("semantic-scene/mujoco-asset", "feature/v060-r1pro-tote-gripper-assets"),
    ("semantic-robot-deployment", "feature/v050-r1pro-runtime-bundle"),
    ("semantic-ability/ability-runtime", None),
    ("ability-framework/abilityframework", "v2.1.0"),
    ("ability-framework/ability-py-sdk", "v0.4.0"),
    ("ability-framework/ability-scaffold", "v1.2.0"),
]

MARK = {"ok": "✓", "drift": "≠", "missing": "?", "unset": "·"}


def sx(p):
    return os.path.expandvars(os.path.expanduser(p or ""))


def run(cmd, cwd=None, timeout=60):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 1, str(e)


def load_manifest(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
        repos = d.get("repos")
        if isinstance(repos, dict):
            return d
    except Exception:
        pass
    return {"version": 1, "updated": "", "repos": {}}


def freeze_release(base, data, name, outdir="releases"):
    """把工作区各仓库当前 HEAD 固化为 commit 级发布快照 (可复现构建的事实来源)"""
    rel = {"version": 1, "release": name, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "repos": {}}
    for local, _d in REPOS:
        kind, ref, commit = current_ref(repo_dir(base, local))
        if kind == "missing":
            continue
        rel["repos"][local] = {"ref": ref, "kind": kind, "commit": commit}
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, f"{name}.json")
    json.dump(rel, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return path, len(rel["repos"])


def save_manifest(path, data):
    data["version"] = 1
    data["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return data["updated"]


def repo_dir(base, local):
    return os.path.join(base, local)


def remote_short(path):
    """origin 短地址 (去 scheme/host/.git/kernel/ 前缀, 超 32 截断); 有 upstream 远端加 ↑ (fork);
    目录缺失返回 '-'"""
    if not os.path.isdir(os.path.join(path, ".git")):
        return "-"
    rc, out = run(["git", "-C", path, "remote", "get-url", "origin"])
    if rc != 0 or not out:
        return "-"
    url = out.splitlines()[0]
    for pfx in ("https://", "http://", "ssh://git@"):
        if url.startswith(pfx):
            url = url[len(pfx):]
            break
    url = url.split("@")[-1]
    url = url.split("/", 1)[1] if "/" in url else url
    url = url.removesuffix(".git")
    if url.startswith("kernel/"):
        url = url[len("kernel/"):]
    if len(url) > 32:
        url = url[:31] + "…"
    rc2, _u = run(["git", "-C", path, "remote", "get-url", "upstream"])
    if rc2 == 0:
        url += " ↑"
    return url


def current_ref(path):
    """返回 (类型, ref, commit8); 目录不存在 -> (missing, '', '')"""
    if not os.path.isdir(os.path.join(path, ".git")):
        return ("missing", "", "")
    rc, out = run(["git", "-C", path, "symbolic-ref", "--quiet", "--short", "HEAD"])
    if rc == 0 and out:
        rc2, c = run(["git", "-C", path, "rev-parse", "--short", "HEAD"])
        return ("branch", out, c[:8])
    rc, out = run(["git", "-C", path, "describe", "--tags", "--exact-match"])
    if rc == 0 and out:
        rc2, c = run(["git", "-C", path, "rev-parse", "--short", "HEAD"])
        return ("tag", out.splitlines()[-1], c[:8])
    rc, c = run(["git", "-C", path, "rev-parse", "--short", "HEAD"])
    return ("commit", c[:8], c[:8])


def remote_refs(path):
    """远端分支与 Tag 列表 [(kind, name)]; 失败返回 []"""
    if not os.path.isdir(os.path.join(path, ".git")):
        return []
    rc, out = run(["git", "-C", path, "ls-remote", "--heads", "--tags", "origin"], timeout=90)
    if rc != 0:
        return []
    seen, refs = set(), []
    for ln in out.splitlines():
        parts = ln.split("\t")
        if len(parts) != 2:
            continue
        ref = parts[1]
        if ref.endswith("^{}"):
            continue
        if ref.startswith("refs/heads/"):
            k, n = "branch", ref[len("refs/heads/"):]
        elif ref.startswith("refs/tags/"):
            k, n = "tag", ref[len("refs/tags/"):]
        else:
            continue
        if n not in seen:
            seen.add(n)
            refs.append((k, n))
    refs.sort(key=lambda x: (x[0], x[1]))
    return refs


def checkout(path, ref):
    rc1, o1 = run(["git", "-C", path, "fetch", "origin", "--tags", "--prune"], timeout=300)
    rc2, o2 = run(["git", "-C", path, "checkout", "-q", ref], timeout=120)
    if rc2 != 0:
        rc2b, o2b = run(["git", "-C", path, "switch", "-C", ref, "--track", f"origin/{ref}"], timeout=120)
        if rc2b != 0:
            return False, (o1 + "\n" + o2 + "\n" + o2b).strip()[:400]
        o2 = o2b
    rc3, c = run(["git", "-C", path, "rev-parse", "--short", "HEAD"])
    return True, c[:8]


def adopt_all(base, data):
    n = 0
    for local, _d in REPOS:
        kind, ref, commit = current_ref(repo_dir(base, local))
        if kind in ("branch", "tag") and ref:
            data["repos"][local] = {"ref": ref, "commit": commit}
            n += 1
        elif kind == "commit":
            data["repos"][local] = {"ref": commit, "commit": commit}
            n += 1
    return n


# ---------------- TUI ----------------

def norm_key(ch):
    if isinstance(ch, str) and len(ch) == 1:
        return ord(ch)
    return ch


class TUI:
    def __init__(self, cfg_path, base):
        self.cfg_path = cfg_path
        self.base = base
        self.data = load_manifest(cfg_path)
        self.sel = 0
        self.logs = []
        self.quit = False
        self.focus = "table"
        self.log_offset = 0
        self.dirty = True
        self.states = {}
        self.remotes = {}

    def log(self, msg):
        self.logs.append((time.strftime("%H:%M:%S"), msg))
        self.logs = self.logs[-500:]
        self.dirty = True

    def refresh_states(self):
        for local, _d in REPOS:
            d = repo_dir(self.base, local)
            self.states[local] = current_ref(d)
            self.remotes[local] = remote_short(d)
        self.dirty = True

    def row_status(self, local):
        conf = self.data["repos"].get(local, {}).get("ref", "")
        kind, cur, _c = self.states.get(local, ("missing", "", ""))
        if not conf:
            return "unset"
        if kind == "missing":
            return "missing"
        return "ok" if conf == cur else "drift"

    # ---- 绘制 ----
    def draw(self, stdscr):
        H, W = stdscr.getmaxyx()
        if H < 16 or W < 100:
            stdscr.erase()
            stdscr.addstr(0, 0, "终端太小, 请至少 100x16", curses.A_BOLD)
            stdscr.refresh()
            return
        stdscr.erase()
        head = f" 子仓库版本清单  工作区: {self.base}  配置: {self.cfg_path}"
        stdscr.addstr(0, 0, head[:W - 1], curses.A_BOLD | curses.color_pair(3))
        # 顶栏/底栏先写入 stdscr 并 noutrefresh, 再刷新子窗;
        # 若末尾再 stdscr.refresh() 会用空白把两个子窗整体盖掉 (只剩上下两栏)
        keys = " Enter:改ref p:远端选择 c:同步选中 C:同步全部 a:采纳当前 s:保存 r:重载 ?:帮助 q:退出"
        stdscr.addstr(H - 1, 0, keys[:W - 1], curses.color_pair(3) | curses.A_DIM)
        stdscr.noutrefresh()
        th = max(6, min(H - 4, len(REPOS) + 4))  # 尽量全部仓库单屏可见
        # 表格窗
        tw = curses.newwin(th, W, 1, 0)
        tw.box()
        tw.addstr(0, 2, " 仓库 (↑↓ 选择, Enter 输入, p 远端列表, c 同步, a 采纳当前, s 保存) ",
                  curses.A_BOLD | curses.color_pair(3))
        cols = f" {'':2} {'仓库':<36} {'远端':<32} {'清单 ref':<28} {'工作区当前'}"
        tw.addstr(1, 1, cols[:W - 4], curses.A_BOLD)
        first = max(0, min(self.sel - th + 4, len(REPOS) - th + 3))
        first = max(0, min(first, self.sel))
        y = 2
        for i in range(first, len(REPOS)):
            if y >= th - 1:
                break
            local, _d = REPOS[i]
            st = self.row_status(local)
            conf = self.data["repos"].get(local, {}).get("ref", "") or "-"
            kind, cur, commit = self.states.get(local, ("missing", "", ""))
            cur_txt = {"branch": f"{cur}", "tag": f"{cur} (tag)",
                       "commit": f"{cur} (detached)", "missing": "目录缺失"}[kind] if kind != "missing" else "目录缺失"
            if commit and kind in ("branch", "tag"):
                cur_txt += f" @{commit}"
            mark = MARK[st]
            rem = self.remotes.get(local, "-")
            line = f" {mark:<2} {local:<38} {rem:<34} {conf:<30} {cur_txt}"
            attr = {"ok": curses.color_pair(1), "drift": curses.color_pair(4),
                    "missing": curses.color_pair(2), "unset": 0}[st]
            if i == self.sel:
                attr |= curses.A_REVERSE
            tw.addstr(y, 1, line[:W - 3], attr)
            y += 1
        tw.refresh()
        # 日志窗
        lw = curses.newwin(H - th - 2, W, th + 1, 0)
        LW, LWW = lw.getmaxyx()
        lw.box()
        lw.addstr(0, 2, " 操作日志 ", curses.A_BOLD | curses.color_pair(3))
        shown = []
        for ts, msg in self.logs[-60:]:
            for seg in str(msg).splitlines()[:6]:
                shown.append(f"{ts} {seg}")
        start = max(0, len(shown) - (LW - 2) - self.log_offset)
        for i, ln in enumerate(shown[start:start + LW - 2]):
            lw.addstr(1 + i, 1, ln[:LWW - 2])
        lw.refresh()

    # ---- 对话框 ----
    def modal(self, stdscr, w, h, title):
        H, W = stdscr.getmaxyx()
        x, y = max(0, (W - w) // 2), max(0, (H - h) // 2)
        win = curses.newwin(h, w, y, x)
        win.erase()
        win.box()
        win.addstr(0, 2, f" {title} "[:w - 4], curses.A_BOLD | curses.color_pair(3))
        return win

    def input_dlg(self, stdscr, title, prompt, initial=""):
        win = self.modal(stdscr, 70, 7, title)
        win.addstr(1, 2, prompt[:66])
        buf = list(initial)
        stdscr.timeout(-1)
        curses.curs_set(1)
        try:
            while True:
                win.addstr(3, 2, " " * 66)
                win.addstr(3, 2, "".join(buf)[-62:], curses.A_REVERSE)
                win.addstr(5, 2, " Enter 保存    Esc 取消 ", curses.A_DIM)
                win.refresh()
                ch = stdscr.get_wch()
                if ch == "\x1b":
                    return None
                if ch in ("\n", "\r"):
                    return "".join(buf).strip()
                if ch in (curses.KEY_BACKSPACE, "\x7f", "\b"):
                    if buf:
                        buf.pop()
                elif isinstance(ch, str) and ch.isprintable():
                    buf.append(ch)
        finally:
            curses.curs_set(0)
            stdscr.timeout(120)

    def confirm(self, stdscr, title, text):
        win = self.modal(stdscr, 64, 6, title)
        win.addstr(1, 2, text[:60])
        win.addstr(4, 2, " [y] 确认    其他取消 ", curses.A_BOLD)
        win.refresh()
        stdscr.timeout(-1)
        try:
            ch = norm_key(stdscr.get_wch())
        finally:
            stdscr.timeout(120)
        return ch == ord("y")

    def picker(self, stdscr, local):
        d = repo_dir(self.base, local)
        self.log(f"[{local}] 拉取远端分支/Tag 列表…")
        self.draw(stdscr)
        refs = remote_refs(d)
        if not refs:
            self.log(f"[{local}] 无远端仓库或拉取失败 (目录缺失/网络), 可 Enter 手动输入")
            return None
        sel = 0
        top = 0
        stdscr.timeout(-1)
        try:
            while True:
                H, W = stdscr.getmaxyx()
                h, w = H - 4, min(W - 4, 60)
                win = self.modal(stdscr, w, h, f"{local}: 选择 branch / tag  (↑↓ 选, 输入过滤, Enter 确认, Esc 取消)")
                flt = getattr(self, "_flt", "")
                items = [(k, n) for k, n in refs if flt in n]
                if sel >= len(items):
                    sel = max(0, len(items) - 1)
                win.addstr(1, 2, f"过滤: {flt}"[:w - 22], curses.A_REVERSE)
                # 滚动窗口: 可见容量 cap = h-4 行; 保证 sel 始终在窗口内
                cap = max(1, h - 4)
                if sel < top:
                    top = sel
                if sel > top + cap - 1:
                    top = sel - cap + 1
                top = max(0, top)
                for i in range(top, min(len(items), top + cap)):
                    y = 2 + i - top
                    k, n = items[i]
                    mark = "B" if k == "branch" else "T"
                    attr = curses.A_REVERSE if i == sel else (curses.color_pair(5) if k == "tag" else 0)
                    win.addstr(y, 2, f" [{mark}] {n}"[:w - 4], attr)
                info = f"{sel + 1}/{len(items)}"
                if top > 0:
                    info = "↑更多 " + info
                if top + cap < len(items):
                    info += " ↓更多"
                win.addstr(1, w - len(info) - 3, info, curses.color_pair(4))
                win.refresh()
                ch = norm_key(stdscr.get_wch())
                if ch == 27:
                    return None
                if ch in (10, 13) and items:
                    return items[sel][1]
                if ch in (curses.KEY_UP, ord("k")):
                    sel = max(0, sel - 1)
                elif ch in (curses.KEY_DOWN, ord("j")):
                    sel = min(len(items) - 1, sel + 1)
                elif ch == curses.KEY_PPAGE:
                    sel = max(0, sel - cap)
                elif ch == curses.KEY_NPAGE:
                    sel = min(len(items) - 1, sel + cap)
                elif ch == curses.KEY_HOME:
                    sel = 0
                elif ch in (curses.KEY_END, ord("G")):
                    sel = len(items) - 1
                elif ch == curses.KEY_BACKSPACE or ch in (127, 8):
                    self._flt = flt[:-1]
                elif 32 <= ch < 127:
                    self._flt = flt + chr(ch)
        finally:
            stdscr.timeout(120)
            self._flt = ""

    # ---- 动作 ----
    def do_edit(self, stdscr, local):
        cur = self.data["repos"].get(local, {}).get("ref", "")
        v = self.input_dlg(stdscr, f"{local}: 设置 ref (branch/tag/commit)",
                           "输入分支名 / Tag / commit:", initial=cur)
        if v is None:
            return
        if not v:
            self.data["repos"].pop(local, None)
            self.log(f"[{local}] 已清除清单 ref")
        else:
            self.data["repos"][local] = {"ref": v, "commit": ""}
            self.log(f"[{local}] 清单 ref -> {v}")

    def do_pick(self, stdscr, local):
        v = self.picker(stdscr, local)
        if v:
            self.data["repos"][local] = {"ref": v, "commit": ""}
            self.log(f"[{local}] 清单 ref -> {v} (来自远端列表)")

    def do_sync(self, local):
        conf = self.data["repos"].get(local, {}).get("ref", "")
        if not conf:
            self.log(f"[{local}] 未设置清单 ref, 跳过")
            return
        d = repo_dir(self.base, local)
        self.log(f"[{local}] fetch + checkout {conf} …")
        ok, info = checkout(d, conf)
        if ok:
            self.data["repos"][local]["commit"] = info
            self.log(f"[{local}] 已同步到 {conf} @ {info}")
        else:
            self.log(f"[{local}] 同步失败: {info[:200]}")
        self.states[local] = current_ref(d)

    def do_sync_all(self):
        for local, _d in REPOS:
            if self.data["repos"].get(local, {}).get("ref"):
                self.do_sync(local)

    def run(self, stdscr):
        curses.curs_set(0)
        stdscr.keypad(True)
        stdscr.timeout(120)
        try:
            curses.start_color()
            curses.use_default_colors()
            for i, c in ((1, curses.COLOR_GREEN), (2, curses.COLOR_RED),
                         (3, curses.COLOR_CYAN), (4, curses.COLOR_YELLOW),
                         (5, curses.COLOR_MAGENTA)):
                curses.init_pair(i, c, -1)
        except Exception:
            pass
        self.refresh_states()
        self.log(f"已加载 {self.cfg_path} ({len(self.data['repos'])} 项); 工作区 {self.base}")
        while not self.quit:
            if self.dirty:
                self.draw(stdscr)
                self.dirty = False
            try:
                ch = norm_key(stdscr.get_wch())
            except curses.error:
                ch = -1
            if ch == -1:
                self.dirty = True
                continue
            self.dirty = True
            local = REPOS[self.sel][0]
            if ch in (ord("q"), 27):
                if self.dirty_changed() and not self.confirm(stdscr, "退出", "有未保存修改, 仍退出?"):
                    continue
                self.quit = True
            elif ch in (curses.KEY_UP, ord("k")):
                self.sel = max(0, self.sel - 1)
            elif ch in (curses.KEY_DOWN, ord("j")):
                self.sel = min(len(REPOS) - 1, self.sel + 1)
            elif ch in (10, 13):
                self.do_edit(stdscr, local)
                self.refresh_states()
            elif ch == ord("p"):
                self.do_pick(stdscr, local)
                self.refresh_states()
            elif ch == ord("c"):
                self.do_sync(local)
            elif ch == ord("C"):
                self.do_sync_all()
            elif ch == ord("a"):
                n = adopt_all(self.base, self.data)
                self.log(f"已采纳当前 {n} 个仓库的 HEAD 为清单 ref")
                self.refresh_states()
            elif ch == ord("s"):
                ts = save_manifest(self.cfg_path, self.data)
                self.log(f"已保存 {self.cfg_path} ({ts})")
            elif ch == ord("r"):
                self.data = load_manifest(self.cfg_path)
                self.refresh_states()
                self.log("已重新加载清单")
            elif ch == ord("?"):
                self.help_dlg(stdscr)

    def dirty_changed(self):
        return json.dumps(self.data, sort_keys=True) != json.dumps(load_manifest(self.cfg_path), sort_keys=True)

    def help_dlg(self, stdscr):
        win = self.modal(stdscr, 74, 14, "帮助")
        lines = [
            " ↑↓ 选择   Enter 输入 ref(branch/tag/commit, 留空清除)",
            " p  从远端分支/Tag 列表选择 (可输入字符过滤)",
            " c  同步选中仓库: fetch + checkout 到清单 ref",
            " C  同步全部已配置仓库",
            " a  采纳工作区各仓库当前 HEAD 为清单 (稳定后提交本文件)",
            " s  保存清单   r  重新加载   q  退出",
            "",
            " 清单 repo-versions.json 随 quick-start 提交/打 tag,",
            " 即可锁定全部子仓库版本; semantic_installer 2.2 优先读它构建。",
            " ≠=工作区与清单不一致  ?=目录缺失  ·=未配置",
        ]
        for i, ln in enumerate(lines):
            win.addstr(1 + i, 2, ln[:70])
        win.refresh()
        stdscr.timeout(-1)
        try:
            stdscr.get_wch()
        finally:
            stdscr.timeout(120)


def default_config_path(base):
    """清单自动寻址: 脚本目录 -> 同级 quick-start 目录 -> $SEMANTIC;
    都不存在时回脚本目录 (保存时新建)。避免镜像副本各自为政、清单被"重新初始化"。"""
    here = Path(__file__).resolve().parent
    cands = [here / "repo-versions.json",
             here.parent / "quick-start" / "repo-versions.json",
             Path(base) / "repo-versions.json"]
    for c in cands:
        if c.is_file():
            return str(c)
    return str(cands[0])


def main():
    ap = argparse.ArgumentParser(description="Semantic 子仓库版本清单 TUI")
    ap.add_argument("--config", default=None, help="清单文件 (默认脚本目录 repo-versions.json)")
    ap.add_argument("--semantic", default=None, help="工作区根目录 (默认 $SEMANTIC 或 $HOME/workspace/semantic)")
    ap.add_argument("--freeze", default=None, metavar="NAME",
                    help="非交互: 把工作区各仓库当前 HEAD 固化为 releases/<NAME>.json 发布快照")
    args = ap.parse_args()
    base = sx(args.semantic) or os.environ.get("SEMANTIC") or "$HOME/workspace/semantic"
    base = sx(base)
    cfg = sx(args.config) or default_config_path(base)
    if args.freeze:
        data = load_manifest(cfg)
        path, n = freeze_release(base, data, args.freeze)
        print(f"发布快照已生成: {path} ({n} 个仓库, 已锁定到 commit)")
        return 0
    t = TUI(cfg, base)
    curses.wrapper(lambda s: t.run(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
