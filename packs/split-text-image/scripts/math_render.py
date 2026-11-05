#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""figforge :: math_render —— LaTeX 数学子集 → 纯 CSS/HTML（离线可开, 不引 MathJax/KaTeX）

宪法第零条: 转录/排版优先采用 skills/image-ocr-svg-redraw 的方法 —— 本模块把
text.md 中的 $...$ / $$...$$ 公式渲染成技能 output-templates.md 同款的
纯 CSS 数学排版（.mat/.bk/.bd 方括号矩阵、<sup>/<sub>、.frac 分式），
离线打开即正确显示。

支持的子集（覆盖本书页面实际出现的全部记号）:
  * \boldsymbol{v} \mathbf{R} \mathrm{T} \text{and} \operatorname{f}
  * ^{...} _{...}（含单字符形式 x^2, v_1）
  * \begin{bmatrix} a & b \\ c & d \end{bmatrix}（bmatrix/pmatrix/Bmatrix/vmatrix）
  * \frac{a}{b} \sqrt{x} \boxed{...}
  * 希腊字母（\Lambda \Sigma \pi ...）、常用符号（\times \cdot \pm \le \ge \ne
    \approx \rightarrow \infty \sum ...）
  * 间距: \quad \qquad \, \: \; \(空格) \!
  * \left[ \right] 等定界符（含 \{ \} | ）
  * 普通字母斜体（数学约定）、数字/运算符/括号直立、"-" 转真减号 −
  * 未知命令 → 原样保留（宁可可见也不静默吞掉, 宪法第九条诚实渲染）

用法:
  import math_render
  math_render.render(r"\boldsymbol{v} = \begin{bmatrix}1\\2\end{bmatrix}")
"""
import html as _html
import re

GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "vartheta": "ϑ",
    "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ",
    "pi": "π", "rho": "ρ", "sigma": "σ", "varsigma": "ς", "tau": "τ",
    "upsilon": "υ", "phi": "φ", "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π",
    "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
}

SYMBOLS = {
    "times": "×", "div": "÷", "cdot": "·", "pm": "±", "mp": "∓", "ast": "∗",
    "circ": "∘", "bullet": "•", "star": "⋆",
    "cdots": "⋯", "dots": "…", "ldots": "…", "vdots": "⋮", "ddots": "⋱",
    "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "neq": "≠", "ne": "≠",
    "approx": "≈", "equiv": "≡", "sim": "∼", "simeq": "≃", "cong": "≅", "propto": "∝",
    "subset": "⊂", "subseteq": "⊆", "supset": "⊃", "supseteq": "⊇",
    "in": "∈", "notin": "∉", "ni": "∋", "cup": "∪", "cap": "∩", "emptyset": "∅",
    "rightarrow": "→", "to": "→", "leftarrow": "←", "leftrightarrow": "↔",
    "Rightarrow": "⇒", "Leftarrow": "⇐", "mapsto": "↦",
    "infty": "∞", "partial": "∂", "nabla": "∇", "hbar": "ℏ",
    "sum": "∑", "prod": "∏", "coprod": "∐", "int": "∫", "oint": "∮",
    "forall": "∀", "exists": "∃", "neg": "¬", "lnot": "¬", "land": "∧", "lor": "∨",
    "angle": "∠", "perp": "⊥", "parallel": "∥", "mid": "|", "prime": "′",
    "ell": "ℓ", "aleph": "א", "wp": "℘", "Re": "ℜ", "Im": "ℑ",
}

# \, \: \; \  \! 与 \quad \qquad —— 用实体, 浏览器可换行处理更稳
SPACES = {
    ",": "&thinsp;", ":": "&thinsp;", ";": "&thinsp;",
    " ": "&nbsp;", "!": "",
    "quad": "&emsp;", "qquad": "&emsp;&emsp;",
}

# bmatrix/pmatrix/Bmatrix/vmatrix → 括号类名
MAT_ENV = {
    "bmatrix": ("bk l", "bk r"),        # 方括号 [ ]
    "pmatrix": ("bk pl", "bk pr"),      # 圆括号 ( )
    "Bmatrix": ("bk cl", "bk cr"),      # 花括号 { }
    "vmatrix": ("bar l", "bar r"),      # 竖线 | |
    "matrix": ("", ""),                 # 无括号
}


def esc(t: str) -> str:
    return _html.escape(t, quote=False)


class _Parser:
    """递归下降解析器。up=True 时字母不斜体（text/mathrm/mathbf 上下文）。"""

    def __init__(self, s: str, up: bool = False):
        self.s = s
        self.i = 0
        self.up = up

    # ---- 基础 ----
    def _group(self) -> str:
        """消费一个 {...} 组并返回内层原文; 指针在 '{' 上则先跳过。"""
        if self.i < len(self.s) and self.s[self.i] == "{":
            self.i += 1
        depth, j = 1, self.i
        while j < len(self.s) and depth:
            if self.s[j] == "{":
                depth += 1
            elif self.s[j] == "}":
                depth -= 1
            j += 1
        inner = self.s[self.i:j - 1] if depth == 0 else self.s[self.i:j]
        self.i = j
        return inner

    def _word(self) -> str:
        m = re.match(r"[a-zA-Z]+", self.s[self.i:])
        if m:
            self.i += len(m.group(0))
            return m.group(0)
        c = self.s[self.i] if self.i < len(self.s) else ""
        self.i += 1
        return c

    def _token(self) -> str:
        """上下标的操作数: {...} 或单字符或 \命令。"""
        if self.i >= len(self.s):
            return ""
        c = self.s[self.i]
        if c == "{":
            self.i += 1
            return _Parser(self._group(), self.up).parse()
        if c == "\\":
            return self._command()
        self.i += 1
        if c == "-":
            return "−"
        if c.isalpha() and not self.up:
            return f"<i>{esc(c)}</i>"
        return esc(c)

    # ---- 命令 ----
    def _command(self) -> str:
        self.i += 1  # 跳过反斜杠
        name = self._word()

        if name in ("text", "mathrm", "operatorname", "textrm"):
            inner = self._group() if self.i < len(self.s) and self.s[self.i] == "{" else ""
            return esc(inner) if inner else esc(name)
        if name in ("mathbf", "bm", "bold", "symbf"):
            if name == "mathbf":  # 粗直立
                inner = self._group()
                return f"<b>{_Parser(inner, up=True).parse()}</b>"
            inner = self._group()  # 粗斜体（向量约定）
            return f"<b>{_Parser(inner, up=False).parse()}</b>"
        if name in ("boldsymbol", "mathit", "mathsf"):
            inner = self._group()
            return _Parser(inner, up=False).parse()
        if name == "frac" or name == "dfrac" or name == "tfrac":
            num = self._token_src()
            den = self._token_src()
            return (f'<span class="frac"><span class="num">'
                    f"{_Parser(num, self.up).parse()}</span>"
                    f'<span class="den">{_Parser(den, self.up).parse()}</span></span>')
        if name == "sqrt":
            if self.i < len(self.s) and self.s[self.i] == "[":
                self._skip_optional()
            inner = self._token_src()
            return f'√<span class="rad">{_Parser(inner, self.up).parse()}</span>'
        if name == "boxed":
            inner = self._token_src()
            return f'<span class="boxed">{_Parser(inner, self.up).parse()}</span>'
        if name == "begin":
            env = self._group() if self.i < len(self.s) and self.s[self.i] == "{" else ""
            return self._matrix(env)
        if name in ("left", "right", "big", "Big", "bigg", "Bigg", "bigl", "bigr"):
            return self._delim()
        if name == "\\":
            return "<br>"
        if name in SPACES:
            return SPACES[name]
        if name in GREEK:
            return GREEK[name]
        if name in SYMBOLS:
            return SYMBOLS[name]
        if name == "hline" or name == "cline":
            return ""
        # 未知命令: 原样保留（诚实渲染, 第九条）
        return esc("\\" + name)

    def _token_src(self) -> str:
        """frac/sqrt/boxed 的操作数, 返回原文再统一渲染。"""
        if self.i >= len(self.s):
            return ""
        if self.s[self.i] == "{":
            self.i += 1
            return self._group()
        if self.s[self.i] == "\\":
            j = self.i
            self.i += 1
            self._word()
            return self.s[j:self.i]
        c = self.s[self.i]
        self.i += 1
        return c

    def _skip_optional(self) -> None:
        depth, j = 0, self.i
        while j < len(self.s):
            if self.s[j] == "[":
                depth += 1
            elif self.s[j] == "]":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        self.i = j

    def _delim(self) -> str:
        """left/right 后的定界符: 单字符或反斜杠命令。"""
        if self.i >= len(self.s):
            return ""
        if self.s[self.i] == "\\":
            self.i += 1
            d = self._word()
            mapping = {"{": "{", "}": "}", "|": "‖",
                       "langle": "⟨", "rangle": "⟩", "lfloor": "⌊", "rfloor": "⌋",
                       "lceil": "⌈", "rceil": "⌉", "uparrow": "↑", "downarrow": "↓"}
            return mapping.get(d, d if d not in ("", ".") else "")
        c = self.s[self.i]
        self.i += 1
        return "" if c == "." else esc(c)

    def _matrix(self, env: str) -> str:
        end = "\\end{" + env + "}"
        k = self.s.find(end, self.i)
        if k < 0:
            self.i = len(self.s)
            return esc("\\begin{" + env + "}")
        content = self.s[self.i:k]
        self.i = k + len(end)
        lcls, rcls = MAT_ENV.get(env, ("bk l", "bk r"))
        rows = [r for r in re.split(r"\\\\", content) if r.strip()]
        grid = []
        for r in rows:
            grid.append([_Parser(c, self.up).parse() for c in r.split("&")])
        ncols = max(len(r) for r in grid) if grid else 1
        # 用 CSS grid + span 而非 <table>: HTML 解析器会在 <p> 内用 <table> 强制
        # 闭段, 把矩阵拆出排版流（实战踩坑）—— span/grid 无此问题
        cells = ""
        for r in grid:
            for c in r:
                cells += f'<span class="mc">{c}</span>'
            cells += '<span class="mc empty"></span>' * (ncols - len(r))
        return (f'<span class="mat"><span class="{lcls}"></span>'
                f'<span class="bd" style="grid-template-columns:repeat({ncols},auto)">{cells}</span>'
                f'<span class="{rcls}"></span></span>')

    # ---- 主循环 ----
    def parse(self, stop_group: bool = False) -> str:
        out = []
        while self.i < len(self.s):
            c = self.s[self.i]
            if stop_group and c == "}":
                self.i += 1
                return "".join(out)
            if c == "\\":
                out.append(self._command())
            elif c == "{":
                self.i += 1
                out.append(_Parser(self._group(), self.up).parse())
            elif c == "}":
                self.i += 1
                out.append("}")
            elif c in "^_":
                self.i += 1
                tag = "sup" if c == "^" else "sub"
                out.append(f"<{tag}>{self._token()}</{tag}>")
            elif c == "&":
                self.i += 1
                out.append(" ")
            elif c == "$":
                self.i += 1
            elif c == "-":
                self.i += 1
                out.append("-" if self.up else "−")
            elif c.isalpha():
                j = self.i
                while j < len(self.s) and self.s[j].isalpha():
                    j += 1
                word = self.s[self.i:j]
                self.i = j
                out.append(esc(word) if self.up else f"<i>{esc(word)}</i>")
            elif c.isspace():
                self.i += 1
                out.append(" ")
            else:
                self.i += 1
                out.append(esc(c))
        return "".join(out)


def render(latex: str) -> str:
    """LaTeX 子集 → HTML 片段（公式内层; 外层包装由调用方负责）。"""
    if not latex or not latex.strip():
        return ""
    return _Parser(latex.strip()).parse()


def linearize(latex: str) -> str:
    """aria-label 用线性化文本: 去命令名、保留内容。"""
    s = re.sub(r"\\(?:begin|end)\{[a-z]*matrix\}", " | ", latex)
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = s.replace("{", "").replace("}", "").replace("\\\\", " | ").replace("&", ",")
    return re.sub(r"\s+", " ", s).strip()


if __name__ == "__main__":
    demo = [
        r"\boldsymbol{v} = \begin{bmatrix}1 \\ 1 \\ -1\end{bmatrix}",
        r"\boldsymbol{u}\boldsymbol{v}^{\mathrm{T}}",
        r"A^{-1}", r"e^{At}", r"[\,1\ \ 1\ \ -1\,]",
        r"M = W^{-1}", r"\Lambda", r"\boldsymbol{v} + \boldsymbol{w}",
    ]
    for d in demo:
        print(f"{d!r:60} -> {render(d)}")
