# Fudan Freshman Test 2026

复旦大学 2026 级研究生入学教育测试辅助工具。项目已升级到 Selenium 4，默认连接：

```text
https://elearning.fudan.edu.cn/courses/113489/quizzes/14232
```

## 本仓库从未在任何地方开放打赏/留微信等，若是有，可能需要确定一下是不是被忽悠了。
## 对于不太熟悉python等的同学，可以使用这里的题库搜索。
https://github.com/Recqvq/Fudan_FreshmanTest2026/blob/main/asset/questions.json

实验室安全测试可以参考 https://github.com/Recqvq/Fudan_SafeTest2026

## 一键开始

电脑需要安装 Chrome 和 [uv](https://docs.astral.sh/uv/)。克隆仓库后执行：

```bash
git clone git@github.com:Recqvq/Fudan_FreshmanTest2026.git
cd Fudan_FreshmanTest2026
uv run fudan-test
```

`uv` 会自动准备 Python、安装锁定版本的依赖并启动 Chrome。首次运行需要在 Chrome 中手动完成复旦统一认证；登录状态保存在本地 `.runtime/`，不会提交到 Git。

默认命令是只读检查：验证登录、测验页面以及“开始/继续测验”按钮，不点击测验、不答题、不提交。

运行完成后 Chrome 默认保持打开，按终端提示回车才会关闭。自动化测试可添加 `--auto-close`。

## 使用方式

只读检查：

```bash
uv run fudan-test
```

根据本地题库选择答案，但不提交：

```bash
uv run fudan-test --execute
```

根据本地题库选择答案并提交：

```bash
uv run fudan-test --execute --submit
```

## 更新题库

题库更新继续采用原仓库的方法：提交当前测验后，从结果页读取正确答案，再合并到 `asset/questions.json`。当前测验可以是空白尝试，也可以是已经选过部分答案的尝试。

先做只读检查：

```bash
uv run fudan-update-bank
```

确认要产生一次提交记录后执行：

```bash
uv run fudan-update-bank --update-bank --confirm-attempt-submit
```

写入新题库前，程序会将旧题库备份为 `asset/questions.before_2026.json`。只有结果页成功解析出正确答案时才会写入题库。

程序会校验每条题库记录：正确答案必须非空且属于该题选项。污染或不完整记录会被跳过，绝不会用于自动勾选或正式提交。

## 安全设计

- 默认只读，不点击任何测验控件。
- 开始或继续测验必须显式传入 `--execute` 或 `--update-bank`。
- 正式提交必须显式传入 `--submit`。
- 题库采集必须同时传入 `--update-bank --confirm-attempt-submit`。
- 账号和密码只在复旦登录页输入，程序不读取或保存密码。
- ChromeDriver 由 Selenium Manager 自动匹配，不再需要手动下载或配置路径。

## 本地验证

```bash
uv run python -m unittest discover -s tests -v
```

当前题库采用以下结构：

```json
{
  "stem": "题干",
  "answers": ["选项一", "选项二"],
  "correct_answers": ["选项一"]
}
```
