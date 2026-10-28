# GitHub 首次上传与后续更新手册

当前项目可作为进行中的作品集仓库发布。已实现普通攻击基线，不宣称已经实现技能、Monte Carlo、分析图或Streamlit。本文记录操作方法，不自动表示GitHub上传已完成。用户随后明确授权自动上传及包含四份已保存Notebook；这些文件的只读隐私检查已通过，并已逐一加入.gitignore白名单。

## 先理解四个位置

```text
工作目录（编辑文件）→ 暂存区（git add）→ 本地历史（git commit）→ GitHub（git push）
```

- 保存文件不等于commit；commit不等于push。
- Git记录文件和提交历史，不会直接备份PostgreSQL服务里的数据库。
- 私有仓库也不应保存密码。不要将网页Upload files拖拽当成.gitignore保护下的git push。

## 首次上传清单

上传：src/、tests/、sql/、docs/、README.md、pyproject.toml、requirements-lock.txt、.env.example、.gitignore、AGENTS.md、scripts/及无敏感内容的占位文件。

当前允许上传：用户明确授权的四份已保存Notebook。暂不上传：其他未经审核的.ipynb、data/raw和data/processed的下载/导出数据、批量日志和未审核的截图。

不能上传：.env、真实密码/Token/API Key、SSH私钥、个人信息、含本机用户名的绝对路径、数据库备份。虚拟环境、缓存、构建产物和.vscode无需上传。

当前.gitignore已排除这些常见本地内容，包括新加的*.ipynb、backups/、db_dumps/和常见备份/密钥文件扩展名。它不会自动从既有Git历史移除秘密；本项目目前没有commit，所以还不存在旧提交泄露问题。

## Notebook必须由用户手动处理

首次只读检查时，磁盘上的`3. database queries.ipynb`与`4. basic combat.ipynb`曾为0字节。用户随后保存了内容，当前四份均为有效Notebook，且未发现本机用户目录路径、已知数据库密码或常见凭据格式。检查未修改内容或输出。今后也不要将内核中的运行结果当成已经保存到文件。

先不要关闭VS Code。在显示完整代码的Notebook标签页按Ctrl+S，核对保存位置；若是Untitled，使用另存为，保存到项目notebooks目录对应文件。确认关闭再打开时仍有代码后，再安排备份。

以后要发布Notebook：

1. 用户手动保存并查看所有代码单元格，移除硬编码凭据和个人路径。
2. 用户在VS Code中选择Clear All Outputs，再保存；如需展示结果，之后仅运行并保留确认可公开的输出。
3. 检查错误堆栈、图片、元数据和打印内容是否包含个人信息。
4. 在.gitignore中把`*.ipynb`换成`*.ipynb`加一个明确的白名单，例如：

```gitignore
*.ipynb
!notebooks/1. data acquisition.ipynb
```

5. 使用带引号的文件路径暂存这份已审阅文件，检查暂存内容再提交。不要用git add -f绕过审核。

助手不创建、修改、覆盖、删除、清除输出或执行Notebook。

## 首次上传：PowerShell流程

所有YOUR_开头的内容都必须换成你自己的值，不能原样执行。命令逐块执行，任何一步报错先停下处理。

### 1. 打开已有桌面项目

```powershell
Set-Location -LiteralPath (Join-Path ([Environment]::GetFolderPath('Desktop')) 'tft-balance-simulator')
git --version
git status
```

仓库已经初始化，分支是main，不要再次git init。助手环境使用的是捆绑Git；用户自己的VS Code终端是否能找到Git，应以上述命令为准。如不能识别，安装官方Git for Windows后重启VS Code。

### 2. 配置当前仓库的提交身份

```powershell
git config user.name "YOUR_GITHUB_USERNAME"
git config user.email "YOUR_GITHUB_NOREPLY_EMAIL"
```

从GitHub Settings > Emails复制完整noreply邮箱，不手工猜ID。这里没有--global，因此只作用于本项目。提交姓名/邮箱会进入历史；它们不是登录凭据。

### 3. 本地检查和测试

```powershell
git check-ignore .env .venv .vscode "notebooks/4. basic combat.ipynb"
.\.venv\Scripts\python.exe -m pytest -q
```

默认预期90 passed、16 skipped，跳过的是需要本地数据库的测试。不要把.env内容粘贴到聊天或GitHub。

### 4. 暂存与查看

```powershell
git add .
git status --short
git diff --cached --name-only
git diff --cached --stat
git diff --cached
```

确认没有.env、.venv、.ipynb或数据文件；.env.example应当存在且密码为空。git diff --cached查看本次真正会提交的内容。若进入分页器，按q退出。

如果首次提交前误暂存某个文件，可运行下面这条，只移出Git暂存区，不删除本机文件：

```powershell
git rm --cached -- "PATH_TO_THE_WRONGLY_STAGED_FILE"
```

### 5. 创建本地首次提交

```powershell
git commit -m "feat: add versioned TFT data pipeline and deterministic combat baseline"
git log -1 --oneline
```

这才是第一个历史记录。不能把现在的文件伪造成过去四个阶段分别提交的历史。

### 6. 在GitHub网页创建空仓库

建议先Private，审核后可改为Public展示。名称`tft-balance-simulator`。当前描述可用：

```text
A Python-based TFT data pipeline and simplified combat simulator using PostgreSQL. Monte Carlo analysis and visualization are planned.
```

不要初始化README、.gitignore或License，以免与已有本地文件形成独立历史。许可证由作者另行选择，不能把第三方游戏数据和资产一并视为原创代码授权。

### 7. 关联并首次推送

```powershell
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/tft-balance-simulator.git
git remote -v
git push -u origin main
```

只配置一次origin。HTTPS通常可通过Git Credential Manager的浏览器登录认证；不要把密码或Token写入remote URL。Git操作不接受普通GitHub账户密码作为HTTPS密码。

刷新仓库网页，确认README和源码可见、没有本地秘密。之后git push无需再次写-u。

## 后续更新

先保存改动、查看diff、运行测试，再按功能提交。示例：

```powershell
git status
git diff
.\.venv\Scripts\python.exe -m pytest -q
git add src tests docs README.md
git diff --cached --stat
git commit -m "feat: add reproducible critical strikes"
git push
```

这只是未来功能完成后的提交示例，当前尚未实现暴击。修改了SQL、依赖或忽略规则时，另把相应文件加入暂存。每完成一个可运行功能做一次有意义的提交，不必每个单元格提交一次。

推荐提交前缀：feat（功能）、fix（修复）、docs（文档）、test（测试）、refactor（结构调整）、chore（配置维护）。消息要描述实际完成内容。

## 分支与版本标记

熟悉基础流程后，可将下一阶段放到独立分支：

```powershell
git switch -c feature/phase5-critical-strikes
```

完成后在该分支提交，再运行：

```powershell
git push -u origin feature/phase5-critical-strikes
```

在GitHub创建Pull Request，查看差异、确认测试，再合并main。合并后回到本地：

```powershell
git switch main
git pull --ff-only origin main
```

独立分支不是第二个项目文件夹。不要重新下载ZIP覆盖本地工作，也不要重新git init。

首次上传确认无误后，可选标记当前基线：

```powershell
git tag -a v0.1.0 -m "Deterministic ordinary-attack combat baseline"
git push origin v0.1.0
```

普通git push不会自动上传所有tag。不要把标签当作新的代码拷贝或数据库备份。

## 同步与常见问题

- 平时优先在本地编辑，避免网页与本地同时改同一文件。
- 如在网页或另一台电脑修改了仓库，先保存并提交本地工作，再用git pull --ff-only。若无法快进，不要force push，先检查历史。
- remote origin already exists：用git remote -v核对，不重复添加。
- nothing to commit：没有新的已暂存改动，或文件尚未保存/被忽略；不是一定报错。
- non-fast-forward：远端有本地未包含的提交，不能直接强推覆盖。
- authentication failed/403：检查登录账号、仓库权限和认证方式，不把Token粘贴到聊天。
- CRLF/LF提示通常是行尾转换提醒，需与真正error区分。
- 如果误推秘密，先撤销/轮换对应凭据，再处理Git历史；仅删除最新文件并不能清除历史。
- 不要在不理解影响时运行reset --hard、clean -fd或push --force。

## 展示、复现和备份边界

- README保留当前进度及模型限制。不能把Monte Carlo、技能或Streamlit写成已完成。
- 当前首次上传包括四份已授权Notebook，但不包括本地数据。新克隆能安装代码并运行离线测试；真实英雄数据库和数据获取步骤仍需手动准备，不能声称已经一键复现全流程。
- 不上传.venv；别人按pyproject.toml或版本快照安装依赖。
- PostgreSQL数据不会随Git上传；原始快照、CSV和数据库备份要在私有位置另外保留。
- 清理后的Notebook、实验图表、小型可分享数据集可以后续单独审核加入，不要一次上传全部缓存/大文件。
- GitHub Actions自动测试尚未配置；git push本身不会自动运行pytest。CI按原计划在后续工程阶段添加。
- 原创代码许可证、第三方数据使用说明、截图、架构图和最终展示将在后续完善，不阻塞当前代码仓库的分阶段发布。

## 官方参考

- 首次上传：https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github
- 认证：https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github
- 提交邮箱：https://docs.github.com/en/account-and-profile/reference/email-addresses-reference
- 忽略文件：https://docs.github.com/en/get-started/git-basics/ignoring-files
- 敏感数据处理：https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
