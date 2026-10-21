# DeepSeek Harness 官方 Windows 桌面端 + dsh-purge 安装、修复与环境配置指南

> 编写日期：2026-10-21（北京时间）。本文记录一次已经完成的 Windows 安装过程，供另一台电脑上的 AI 助手复现。版本号是本次验证基线，不代表今后的最新版本。本文只配置本机软件，不包含对外扫描、远程部署或测试目标。

文档验证：16 段 PowerShell 代码已通过语法解析，2 段 Python 和 1 段 JavaScript 已通过语法检查；cwd 修复脚本在临时硬链接副本上验证了重复运行的幂等性。整理后的整套流程尚未在另一台全新 Windows 上从头执行，执行助手仍须逐项验收。

## 已整理好的本机离线目录（优先使用）

本文配套材料现在位于桌面仓库的 `windows-install/`。配套宿主 EXE 的相对位置为 `windows-install/installers/deepseek-harness-0.2.1-rc.2-win-x64.exe`。

搬到另一台 Windows x64 电脑时，复制完整仓库文件夹或完整的 `windows-install` 文件夹，先阅读其中 `README.md`，运行 `Start-Windows-Setup.cmd`。该目录已包含本文使用的工具和模板、Node/pnpm、Python 安装器、Impacket 离线 wheel；不需要重新下载或在新电脑编译 Masscan。

下文保留在线获取与手工步骤，作为理解原理、排错和重建安装包的参考。**使用现成离线向导时，不要再重复执行在线安装章节。尤其不要把整个含安装材料的仓库复制到插件目录；向导使用独立源码归档。**

离线模式使用 bundled Node/pnpm，因此不要求全局安装 Node/pnpm 或 Git。Python 3.13 x64 仍需在目标电脑安装，以重建本机虚拟环境。Harness 初始化/登录和模型调用可能需要网络。校验和测试边界见 `windows-install/docs/打包验证结果.md`。

## 1. 把这一段交给执行安装的 AI 助手

```text
请阅读完整文档，在这台 Windows 电脑上安装官方 DeepSeek Harness 桌面端、dsh-purge 1.1.71，并按文档配置本机工具环境。

先检查现有软件、实际 DSH_HOME、desktop profile 和系统架构；复用已兼容的安装。不要使用文档作者的用户名或绝对路径。
所有步骤先备份再修改，保留原有依赖、bundle、配置和用户数据。安装工具使用官方来源，验证下载包和可执行性。
只操作 desktop profile；不要顺带安装 web profile。npm 没有 dsh-purge 包，不要执行 pnpm add dsh-purge。
针对本版本的 {{cwd}} 问题，使用文档中的幂等修复，兼顾插件源目录和 node_modules 实际加载副本。
不要直接运行 Linux setup.sh，不要把“文件存在”“ready=true”当成所有技能端到端可用。不要伪造完成标记。
可以完成本地安装、备份、路径配置、版本与帮助检查、依赖检查、模板验证。不要发起目标扫描、连接远程主机或部署隧道。账号密钥与私钥由我在本机配置，不要求贴到聊天里。
如需重启正在使用的 Harness，先确认没有运行任务或未保存内容。遇到 UAC、账号登录或无法可靠操作的驱动安装窗口，请明确指出需要我完成哪一步。
结束时交付实际版本、成功/失败清单、验证证据、剩余依赖、备份位置。只有实测通过的项目才能写“完成”。
```

## 2. 验证基线与边界

### 2.1 原电脑环境

| 项目 | 本次实测 |
|---|---|
| 系统 | Windows 11 专业版，约 32 GB 内存 |
| PowerShell | 7.6.5 |
| Node.js | 26.8.1 |
| Python | 3.13.1 |
| Git | 2.42.0.windows.2 |
| pnpm | 11.25.0 |
| 宿主 | 官方 DeepSeek Harness 桌面端 0.2.1-rc.2 |
| 插件 | dsh-purge 1.1.71 |
| profile | desktop |
| 插件 Git 提交 | `8df4406a7c5bddc01091ed20608417390cb457ee` |

新电脑不要求相同内存。插件声明 Node.js ≥18，Windows 无闪窗要求 ≥22；上面的具体版本是实测记录，不应把原电脑上 Codex 私有的 pnpm 路径复制到新电脑。

本文的脚本以 **PowerShell 7 + Windows x64** 为基线。ARM64 机器不要直接套用所有 amd64 二进制。PowerShell 5.1 的 JSON/UTF-8 行为不同，优先安装 PowerShell 7 再执行。

### 2.2 三种状态要分开

1. **插件已安装**：desktop profile 注册插件且加载副本存在。
2. **本机工具就绪**：15 项工具路径有效，版本/帮助/自测通过，环境状态为 `ready: true`。
3. **全部技能可用**：还涉及外部账号、VPS、额外软件、平台差异和真实任务验证。本次没有达到或宣称这个状态。

本次已经确认：Nmap 7.992 加载 Npcap 1.89，服务运行；15/15 工具被识别；Masscan 自测通过；Impacket 依赖检查通过；Nuclei 单个模板语法验证通过。

`{{cwd}}` 修复已经通过语法和针对性检查，但原对话没有记录修复后成功完成一次模型对话。因此新电脑必须自行完成“重启后发送一条普通消息”的最终验证。

## 3. 路径约定与安装前检查

以下变量在同一个 PowerShell 7 会话中使用。普通安装尽量用当前用户权限；驱动/系统安装器需要管理员授权时交给用户完成。

```powershell
$ErrorActionPreference = 'Stop'
$desktopPath = [Environment]::GetFolderPath('Desktop')
$repoPath = Join-Path $desktopPath 'dsh-purge'
$setupWork = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'dsh-setup-work'
New-Item -ItemType Directory -Path $setupWork -Force | Out-Null

[Runtime.InteropServices.RuntimeInformation]::OSArchitecture
$PSVersionTable.PSVersion
Get-Command node,python,git,pnpm -ErrorAction SilentlyContinue |
    Select-Object Name,Source
node --version
python --version
git --version
pnpm --version
```

缺少软件时，从其官方站点安装：[Node.js](https://nodejs.org/)、[Git for Windows](https://gitforwindows.org/)、[Python](https://www.python.org/downloads/windows/)、[PowerShell](https://github.com/PowerShell/PowerShell/releases)、[pnpm 安装说明](https://pnpm.io/installation)。不要为了复现版本而覆盖机器上已有的正常环境。

若已有 Node/npm、仅缺 pnpm，可以安装本次使用的版本：

```powershell
npm install --global pnpm@11.25.0
if ($LASTEXITCODE -ne 0) { throw 'pnpm 安装失败' }
pnpm --version
```

## 4. 安装固定版本的官方 GUI

- [官方产品页](https://www.deepseek.com/harness/)
- [官方 0.2.1-rc.2 Windows x64 EXE](https://download.deepseek.com/dsh-desk/bin/win-x64/deepseek-harness-0.2.1-rc.2-win-x64.exe)
- [官方版本记录](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.2.1-rc.2)

不要用带 `latest` 的地址来保证固定版本。该版本 GitHub Release 当时只有源码和证明文件，没有桌面 EXE；源码 ZIP 不是安装包。社区桌面版也不等同于这里的官方 EXE。

下载、检查来源和签名后，正常打开安装器完成安装。启动 Harness 一次，让它创建 `desktop` profile。使用你自己的账号完成登录。

默认安装位置通常是：

```text
%LOCALAPPDATA%\Programs\DeepSeek Harness\DeepSeek Harness.exe
```

安装位置或包内 `version` 文件不能单独证明 Harness 版本：本次该文件曾显示 Electron 版本 `44.7.0`，不是 `0.2.1-rc.2`。应核对应用自身显示的 Harness 版本或其实际运行包版本。

## 5. 找到实际 DSH_HOME

默认通常为 `%USERPROFILE%\.dsh`，但可能受环境变量或便携安装影响。不要看到某个 `.dsh` 就直接修改。

```powershell
$dshCandidates = @()
if ($env:DSH_HOME) { $dshCandidates += $env:DSH_HOME }
$dshCandidates += @(
    (Join-Path $env:USERPROFILE '.dsh'),
    (Join-Path $env:APPDATA 'DeepSeek Harness\dsh-home'),
    (Join-Path $env:LOCALAPPDATA 'DeepSeek Harness\dsh-home')
)
$dshCandidates | Select-Object -Unique | Where-Object {
    Test-Path -LiteralPath (Join-Path $_ 'profiles\desktop\package.json')
}
```

如有多个候选，结合运行中的 EXE、启动方式、配置更新时间判断；必要时询问用户实际使用哪个安装。便携版还要检查安装根旁边的 `.dsh`。不要全盘扫描。

确认之后才设置：

```powershell
# 默认值只是示例；若实际位置不同，必须修改这一行。
$dshRoot = Join-Path $env:USERPROFILE '.dsh'
$profileDir = Join-Path $dshRoot 'profiles\desktop'
$profileFile = Join-Path $profileDir 'package.json'
$profileData = Get-Content -LiteralPath $profileFile -Raw | ConvertFrom-Json
if ($profileData.name -ne 'dsh-profile-desktop') {
    throw '不是已确认的 desktop profile，停止修改'
}
$pluginRoot = Join-Path $dshRoot 'plugins\dsh-purge'
$toolkitRoot = Join-Path $dshRoot 'redteam\toolkit'
```

## 6. 获取插件并固定版本

仓库：[YuJunZhiXue/dsh-purge](https://github.com/YuJunZhiXue/dsh-purge)。

```powershell
if (-not (Test-Path -LiteralPath $repoPath)) {
    git clone https://github.com/YuJunZhiXue/dsh-purge.git $repoPath
    if ($LASTEXITCODE -ne 0) { throw '克隆失败' }
}
git -C $repoPath status --short
# 若已有用户修改，先备份并处理，不能直接切换覆盖。
git -C $repoPath checkout --detach 8df4406a7c5bddc01091ed20608417390cb457ee
if ($LASTEXITCODE -ne 0) { throw '无法切到实测提交' }
Get-Content (Join-Path $repoPath 'package.json') -Raw |
    ConvertFrom-Json | Select-Object name,version
```

应显示 `dsh-purge`、`1.1.71`。作者公告计划从 10 月 27 日起停止 GitHub 更新并改变分发渠道；这不保证未来还能在线获取该提交。建议在可访问时保留当前源码备份和许可文件。若仓库不可用，使用自己已保存且来源清楚的副本，不能随意用第三方重打包替代。

不要把旧电脑整个 `.dsh` 复制到新电脑：里面可能有登录凭据、会话和其他个人数据。Python 虚拟环境也应在新电脑重建。

## 7. 安装插件到 desktop profile

先完全退出 Harness。若 `dsh` 命令存在，可以按项目说明在仓库目录执行 `dsh plugin --profile desktop add .`；随后仍要验证实际安装版本与位置。

**本次实际采用的是下面的手动方式**，因为 `dsh` 不在 PATH。

### 7.1 复制插件

```powershell
if (Test-Path -LiteralPath $pluginRoot) {
    throw '插件目标目录已存在。先检查版本和本地修复，备份后再决定是否更新。'
}
New-Item -ItemType Directory -Path (Split-Path $pluginRoot) -Force | Out-Null
Copy-Item -LiteralPath $repoPath -Destination $pluginRoot -Recurse
```

### 7.2 备份并修改 package.json

```powershell
$backupStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
Copy-Item -LiteralPath $profileFile -Destination ($profileFile + '.backup-' + $backupStamp)
$profileData = Get-Content -LiteralPath $profileFile -Raw | ConvertFrom-Json
if (-not $profileData.dependencies) {
    $profileData | Add-Member -NotePropertyName dependencies -NotePropertyValue ([pscustomobject]@{}) -Force
}
$profileData.dependencies | Add-Member -NotePropertyName 'dsh-purge' `
    -NotePropertyValue 'file:../../plugins/dsh-purge' -Force
if ('dsh-purge' -notin @($profileData.dsh.profile.bundles)) {
    $profileData.dsh.profile.bundles = @($profileData.dsh.profile.bundles) + 'dsh-purge'
}
$profileData | ConvertTo-Json -Depth 50 |
    Set-Content -LiteralPath $profileFile -Encoding utf8NoBOM
Push-Location $profileDir
try {
    pnpm install
    if ($LASTEXITCODE -ne 0) { throw 'profile 依赖安装失败' }
} finally { Pop-Location }
Get-Content (Join-Path $profileDir 'node_modules\dsh-purge\package.json') -Raw |
    ConvertFrom-Json | Select-Object name,version
```

保留原来的 `dependencies`、`bundles`、`patchReload` 和其他配置。不要在桌面 profile 中擅自补一个不存在的 `dsh-web-app`，也不要在插件仓库根运行 `pnpm install` 代替 profile 安装。

本次 pnpm 提示缺少 peer `@deepseek-ai/cordis`。宿主有自己的依赖体系，这条警告不等于插件已经失败，也不等于可以忽略所有加载错误。后续必须检查应用实际加载；不要盲目往 profile 塞一个不同版本的 Cordis。

## 8. 修复 unknown prompt variable {{cwd}}

### 8.1 原因及修改范围

本次出现的错误：

```text
unknown prompt variable "{{cwd}}" in section "deployment:persona-suffix";
registered variables: provider, model
```

插件 1.1.71 在两处主动产生该模板变量：

- `cordis.patch.yml`：`personaSuffix: Your working directory is {{cwd}}.`
- `lib/identity.js`：`CWD_ONLY_SUFFIX` 常量；运行时会重新写入 suffix。

只改 YAML 不够；运行时代码仍可能恢复旧值。修复将两处输出改为：

```text
Use the current session working directory for relative paths.
```

这是无模板变量的普通说明，**不会把某台电脑的固定路径写死**。同时保留对旧 suffix 的识别，避免旧内容被当成自定义文本而残留。实际工作目录由宿主上下文或工作目录工具确定。

### 8.2 执行幂等修复

将下面 Python 内容保存到 `$setupWork/fix_cwd.py`。这个版本专门防止源目录与加载副本是硬链接时重复追加条件。

```python
import datetime, pathlib, re, shutil, sys

dsh_root = pathlib.Path(sys.argv[1]).resolve()
roots = [dsh_root / 'plugins/dsh-purge',
         dsh_root / 'profiles/desktop/node_modules/dsh-purge']
old = 'Your working directory is {{cwd}}.'
new = 'Use the current session working directory for relative paths.'
old_const = f'const CWD_ONLY_SUFFIX = "{old}";'
new_const = f'const CWD_ONLY_SUFFIX = "{new}";'
stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')

for root in roots:
    js = root / 'lib/identity.js'
    yaml = root / 'cordis.patch.yml'
    code = js.read_text(encoding='utf-8-sig')
    patch = yaml.read_text(encoding='utf-8-sig')
    if old_const not in code and new_const not in code:
        raise RuntimeError(f'未知插件结构，不做盲目替换：{js}')
    if f'personaSuffix: {old}' not in patch and f'personaSuffix: {new}' not in patch:
        raise RuntimeError(f'未知 personaSuffix，请人工检查：{yaml}')
    a = code.index('function isCwdOnlyText(')
    b = code.index('\nfunction looksLikeOfficialIdentity', a)
    replacement = '''function isCwdOnlyText(text) {
  const t = String(text || "").trim();
  return t === CWD_ONLY_SUFFIX
    || t === "Your working directory is {{cwd}}."
    || t === "Working directory: {{cwd}}."
    || t === "Working directory: {{cwd}}";
}
'''
    updated = (code[:a] + replacement + code[b:]).replace(old_const, new_const)
    new_patch = patch.replace(f'personaSuffix: {old}', f'personaSuffix: {new}')
    for file, before, after in [(js, code, updated), (yaml, patch, new_patch)]:
        if before == after:
            print('ALREADY FIXED', file)
            continue
        shutil.copy2(file, str(file) + '.backup-' + stamp)
        file.write_text(after, encoding='utf-8')
        print('UPDATED', file)
    assert new_const in js.read_text(encoding='utf-8')
    assert f'personaSuffix: {new}' in yaml.read_text(encoding='utf-8')
print('Patch complete; restart Harness and test a conversation.')
```

运行：

```powershell
python (Join-Path $setupWork 'fix_cwd.py') $dshRoot
if ($LASTEXITCODE -ne 0) { throw '修复失败，检查备份和报错' }
node --check (Join-Path $pluginRoot 'lib\identity.js')
if ($LASTEXITCODE -ne 0) { throw '源副本语法检查失败' }
node --check (Join-Path $profileDir 'node_modules\dsh-purge\lib\identity.js')
if ($LASTEXITCODE -ne 0) { throw '加载副本语法检查失败' }
```

说明：旧字符串仍会出现在“识别旧内容”的代码里，不能把全文搜索仍能找到 `{{cwd}}` 当成修复失败。不要无差别替换整个插件所有同名字符串。升级或重新安装插件后要重新判断，修复可能被覆盖；新版本结构不同则停止使用这个补丁。

## 9. 在界面中加载和应用插件

1. 重新打开官方桌面端。
2. 点击会话标题旁的 **dsh-purge**。
3. 在 **清洗 → 应用** 中执行插件自身的应用步骤；这是宿主补丁操作，和写入 profile 不是一回事。
4. 成功后按插件提示重启，再新开一轮对话。
5. 发一条普通消息，确认没有 `{{cwd}}` 解析错误。
6. 进入 **演练台**，由用户阅读并完成其声明/授权步骤。

不要为了图省事强杀正在执行任务的宿主。若没有出现插件按钮，检查实际 profile、安装副本、应用日志和退出是否彻底；不要靠重复安装不同版本解决未知问题。

## 10. Windows 工具环境总览

本次环境目录使用 `$dshRoot/redteam/toolkit`，没有修改全局 PATH。由插件配置保存工具的绝对路径。

| 工作台项目 | 版本 | 安装形式 |
|---|---|---|
| Nmap | 7.992 | 官方安装器，另确认 Npcap 1.89 |
| Nuclei | 3.11.1 | 官方 Windows amd64 ZIP |
| Masscan | 1.3.2 | 官方源码，Visual Studio 2022 编译 |
| fscan | 2.2.2 | 官方 Windows x64 EXE |
| gogo | 2.15.0 | 官方 Windows amd64 EXE |
| suo5 | 2.2.0 | 官方 Windows amd64 EXE |
| frpc / frps | 0.71.1 | 同一个 frp ZIP，两项工具 |
| Chisel | 1.12.0 | 官方 Windows amd64 ZIP |
| ffuf | 2.3.0 | 官方 Windows amd64 ZIP |
| ProjectDiscovery HTTPX | 1.12.0 | 官方 Windows amd64 ZIP |
| DNSX | 1.3.1 | 官方 Windows amd64 ZIP |
| Subfinder | 2.17.0 | 官方 Windows amd64 ZIP |
| ksubdomain | 0.7 | 官方 RAR 中的 Windows EXE |
| Impacket | 0.13.1 | 独立 Python venv |

**不要直接执行插件的 `setup.sh --yes`。** 它主要面向 Kali/Linux，涉及 Linux 包管理器、路径、远程资源及额外组件，不能等同于 Windows 安装方案。

## 11. 安装官方便携工具

下面的下载清单保留本次安装的固定版本和实测 SHA-256。可复制脚本为 `$setupWork/install_portable.py`。它只下载、校验并解压，不运行扫描、不配置远程服务。

对已有目录采用“保留并跳过”策略；跳过后仍必须单独核对版本和可执行性。失败后先检查残留目录，不能把一次失败留下的目录当成成功安装。

```python
import hashlib, json, pathlib, shutil, sys, urllib.request, zipfile

dsh_root = pathlib.Path(sys.argv[1]).resolve()
work = pathlib.Path(sys.argv[2]).resolve()
cache = work / 'downloads'
cache.mkdir(parents=True, exist_ok=True)
toolkit = dsh_root / 'redteam/toolkit'
manifest = json.loads(r'''{
  "nuclei": {
    "url": "https://github.com/projectdiscovery/nuclei/releases/download/v3.11.1/nuclei_3.11.1_windows_amd64.zip",
    "sha256": "bb6cb9ff8939b753f6fcab06fd30a15f5bc61d8382a597871334c007a85ff9d2"
  },
  "httpx": {
    "url": "https://github.com/projectdiscovery/httpx/releases/download/v1.12.0/httpx_1.12.0_windows_amd64.zip",
    "sha256": "14d8ccaa2d95ce9365162682f1a2ba3f14d2000bb4bfb0924af65ec5163ae021"
  },
  "dnsx": {
    "url": "https://github.com/projectdiscovery/dnsx/releases/download/v1.3.1/dnsx_1.3.1_windows_amd64.zip",
    "sha256": "112c2d62d67d26a1b940ed9d10d500d2aa1ee3e3e18393d181ac4969936b9d96"
  },
  "subfinder": {
    "url": "https://github.com/projectdiscovery/subfinder/releases/download/v2.17.0/subfinder_2.17.0_windows_amd64.zip",
    "sha256": "a3fd612928d591fb31c1e59a2e06055e364421ba32251e553073f5673a2d3103"
  },
  "ffuf": {
    "url": "https://github.com/ffuf/ffuf/releases/download/v2.3.0/ffuf_2.3.0_windows_amd64.zip",
    "sha256": "091c8a22d0c7fbe07d343b3ae2c213dbd37b38a8a2ed40631fcd3128ea1764fb"
  },
  "frp": {
    "url": "https://github.com/fatedier/frp/releases/download/v0.71.1/frp_0.71.1_windows_amd64.zip",
    "sha256": "b90074b2b6a1d792a7a40f085ac6d276bcab2d1bc60201f8a86ca53ce65ce821"
  },
  "chisel": {
    "url": "https://github.com/jpillora/chisel/releases/download/v1.12.0/chisel_1.12.0_windows_amd64.zip",
    "sha256": "600a8ad6f03bc7f6d285fd01ab6a3f8a657204adaafa5666ade9451d18df1ebc"
  },
  "fscan": {
    "url": "https://github.com/shadow1ng/fscan/releases/download/v2.2.2/fscan_2.2.2_windows_x64.exe",
    "sha256": "34973a25a3d67077fccd687a46bf6ad737ecac7ea6133a5993915901f193114a"
  },
  "gogo": {
    "url": "https://github.com/chainreactors/gogo/releases/download/v2.15.0/gogo_windows_amd64.exe",
    "sha256": "c3f56039ca1b647d2f64a4c541877638d8d39631eeea7a23f9595cf578a46d87"
  },
  "suo5": {
    "url": "https://github.com/zema1/suo5/releases/download/v2.2.0/suo5-windows-amd64.exe",
    "sha256": "e0e83bbcdae5bddc0cf1367207f454b32b6c110ebfa2a46589c18932fdb946ac"
  }
}''')
failures = []
for name, info in manifest.items():
    dest = toolkit / name
    if dest.exists():
        print('EXISTS: verify version and executable separately:', dest)
        continue
    archive = cache / info['url'].rsplit('/', 1)[-1]
    try:
        partial = archive.with_suffix(archive.suffix + '.partial')
        request = urllib.request.Request(info['url'], headers={'User-Agent': 'Local-Toolkit-Setup'})
        with urllib.request.urlopen(request, timeout=120) as response, partial.open('wb') as out:
            shutil.copyfileobj(response, out)
        digest = hashlib.sha256(partial.read_bytes()).hexdigest()
        if digest.lower() != info['sha256'].lower():
            raise RuntimeError('SHA256 mismatch: ' + name)
        partial.replace(archive)
        if archive.suffix.lower() == '.zip':
            with zipfile.ZipFile(archive) as z:
                for member in z.infolist():
                    target = (dest / member.filename).resolve()
                    if not target.is_relative_to(dest.resolve()):
                        raise RuntimeError('Unsafe archive path')
                dest.mkdir(parents=True)
                z.extractall(dest)
        else:
            dest.mkdir(parents=True)
            shutil.copy2(archive, dest / (name + '.exe'))
        print('INSTALLED:', name, dest)
    except Exception as exc:
        failures.append(name)
        print('FAILED:', name, str(exc))
if failures:
    raise SystemExit('Installation failed: ' + ', '.join(failures))
```

运行：

```powershell
python (Join-Path $setupWork 'install_portable.py') $dshRoot $setupWork
if ($LASTEXITCODE -ne 0) { throw '便携工具安装有失败项' }
```

校验值来自本次实际下载，其中 suo5 没有核对上游发布的校验文件，仅记录了本次文件摘要。哈希一致证明与此记录一致，不等于额外的上游签名认证。未来若官方同名文件变化，应先调查，不能直接删除校验。

## 12. 安装 Nmap 与 Npcap

- [Nmap 官方下载](https://nmap.org/download.html)
- [固定 Nmap 7.992 安装器](https://nmap.org/dist/nmap-7.992-setup.exe)
- [Npcap 官方说明](https://npcap.com/)

```powershell
$nmapInstaller = Join-Path $setupWork 'nmap-7.992-setup.exe'
Invoke-WebRequest 'https://nmap.org/dist/nmap-7.992-setup.exe' -OutFile $nmapInstaller
$nmapHash = (Get-FileHash -LiteralPath $nmapInstaller -Algorithm SHA256).Hash
if ($nmapHash -ne '7D99EE28B2EAE1A90917BB45AFC42C1E900A271E7F1BBE1234CF266A819BACC8') {
    throw 'Nmap 安装器哈希不符'
}
Get-AuthenticodeSignature -LiteralPath $nmapInstaller |
    Select-Object Status,@{Name='Signer';Expression={$_.SignerCertificate.Subject}}
```

本次签名验证结果为 `Valid`、签名者 `Nmap Software LLC`。让用户通过正常安装向导完成 Nmap 和 Npcap。新版驱动可能需要管理员授权或重启，应按实际提示处理。

本次踩过的坑：

- `winget install Insecure.Nmap` 当时提供了旧版 **7.80**，所以不能直接把 winget 安装成功当成所需版本。
- 已有旧版时，新安装器可能先要求卸载旧版；`/S` 曾返回退出码 2。
- Nmap 主程序已经更新，也可能仍在等待 Npcap 安装窗口，不能只看 `nmap.exe` 存在。
- 窗口自动化曾报 `failed to activate captured window`，还返回过与目标不一致的截图。遇到这种情况必须停止猜坐标，交给用户完成；不要连续启动多个安装器。

验证：

```powershell
$nmapCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} 'Nmap\nmap.exe'),
    (Join-Path $env:ProgramFiles 'Nmap\nmap.exe')
)
$nmapPath = $nmapCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $nmapPath) { throw '没有找到 Nmap；如自定义安装，请补充实际路径' }
& $nmapPath --version
Get-Service npcap -ErrorAction SilentlyContinue
Get-Process | Where-Object { $_.ProcessName -match 'nmap.*setup|npcap' } |
    Select-Object ProcessName,Id
```

本次最终看到 `Nmap version 7.992`、`Npcap-1.89`、`npcap Running`，且安装器已退出。

## 13. 安装 ksubdomain 0.7

该官方版本 Windows 资产名是 **`ksubdomain.rar`**，不是带 `windows_amd64` 的 ZIP，自动按文件名筛选会漏掉。

```powershell
$ksubArchive = Join-Path $setupWork 'ksubdomain.rar'
Invoke-WebRequest 'https://github.com/knownsec/ksubdomain/releases/download/v0.7/ksubdomain.rar' -OutFile $ksubArchive
if ((Get-FileHash $ksubArchive -Algorithm SHA256).Hash -ne '4DF2DEFCC02FCA62858D6AB47630FA0AF2A0804FAFEA98E1C02F4C7367EB6B62') {
    throw 'ksubdomain 压缩包哈希不符'
}
tar -tf $ksubArchive
# 本次包内只有 ksubdomain.exe。先核对列表，不接受绝对路径或 .. 路径。
$ksubDir = Join-Path $toolkitRoot 'ksubdomain'
New-Item -ItemType Directory -Path $ksubDir -Force | Out-Null
tar -xf $ksubArchive -C $ksubDir
if ($LASTEXITCODE -ne 0) { throw '解压失败；换用可信解压器，不要伪造成功' }
& (Join-Path $ksubDir 'ksubdomain.exe') --help
& (Join-Path $ksubDir 'ksubdomain.exe') -list-network
```

`-list-network` 只枚举本机网络接口。本次 Windows 自带 `tar` 能解开 RAR；其他 Windows 版本不保证，先检查能力。

## 14. 从源码编译 Masscan 1.3.2

官方 Release 没有可直接匹配的 Windows 安装资产。本次使用本机已有 Visual Studio 2022 Professional 的 C++ 工具链；新电脑可以用支持 v143 工具集的 Visual Studio 2022 / Build Tools 和 Windows SDK。先检查再安装，不能硬编码 Professional 路径。

官方仓库：[robertdavidgraham/masscan](https://github.com/robertdavidgraham/masscan)。

```powershell
$masscanSource = Join-Path $setupWork 'masscan-source'
if (Test-Path -LiteralPath $masscanSource) { throw '源码目录已存在，先检查已有修改' }
git clone --depth 1 --branch 1.3.2 https://github.com/robertdavidgraham/masscan.git $masscanSource
if ($LASTEXITCODE -ne 0) { throw 'Masscan 源码获取失败' }
git -C $masscanSource rev-parse HEAD
# 本次提交：06902c40d1494881c17b7968ef530e1d6bbd320c

$header = Join-Path $masscanSource 'src\string_s.h'
Copy-Item -LiteralPath $header -Destination ($header + '.backup')
$headerText = [IO.File]::ReadAllText($header)
if (-not $headerText.Contains('(_MSC_VER == 1900)')) { throw '源码结构不同，先检查' }
[IO.File]::WriteAllText($header, $headerText.Replace('(_MSC_VER == 1900)', '(_MSC_VER >= 1900)'))

$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path $vswhere)) { throw '需要 Visual Studio C++ 工具链' }
$vsRoot = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsRoot) { throw '未找到 C++ 工具链' }
$msbuildPath = Join-Path $vsRoot 'MSBuild\Current\Bin\MSBuild.exe'
& $msbuildPath (Join-Path $masscanSource 'vs10\masscan.sln') `
    /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=v143 `
    /p:WindowsTargetPlatformVersion=10.0 /verbosity:minimal /nologo
if ($LASTEXITCODE -ne 0) { throw 'Masscan 编译失败' }
$masscanDir = Join-Path $toolkitRoot 'masscan'
New-Item -ItemType Directory -Path $masscanDir -Force | Out-Null
Copy-Item (Join-Path $masscanSource 'bin\masscan.exe') (Join-Path $masscanDir 'masscan.exe')
& (Join-Path $masscanDir 'masscan.exe') --selftest
if ($LASTEXITCODE -ne 0) { throw 'Masscan 内置自测失败' }
```

该修改只是让新版 MSVC 走已有的 Visual Studio 分支；不改扫描逻辑。本次原始构建错误是 `invalid preprocessor command warning` / `C1021`。编译存在上游格式警告，不能把自测通过解释成全面代码审计通过。

`masscan --version` 在这个构建中返回了退出码 1，但打印版本正常；因此用 `--selftest` 的成功结果作主要检查，预期输出 `regression test: success!`。

## 15. 安装 Impacket 独立环境

```powershell
$impacketVenv = Join-Path $toolkitRoot 'impacket-venv'
if (-not (Test-Path -LiteralPath (Join-Path $impacketVenv 'Scripts\python.exe'))) {
    python -m venv $impacketVenv
    if ($LASTEXITCODE -ne 0) { throw '创建 venv 失败' }
}
$impacketPython = Join-Path $impacketVenv 'Scripts\python.exe'
& $impacketPython -m pip install --index-url https://pypi.org/simple 'impacket==0.13.1'
if ($LASTEXITCODE -ne 0) { throw 'Impacket 安装失败' }
& $impacketPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Impacket 依赖检查失败' }
& $impacketPython -c 'from impacket import version; import impacket.smbconnection; print(version.BANNER)'
if ($LASTEXITCODE -ne 0) { throw 'Impacket 导入检查失败' }
```

本次工作台的 `impacket` 项允许填写目录或入口，使用 venv 的 `Scripts` 目录。执行其中 `.py` 脚本时要使用该 venv 的 Python，不能假设系统文件关联会选择正确的解释器。顶层版本已固定，但其传递依赖仍由 pip 解析；另一台电脑需要重新执行 `pip check`，不保证字节级复现。

## 16. 下载和验证 Nuclei 模板

本次 `nuclei -update-templates` 输出“开始安装”后退出，但没有形成可确认的模板目录。因此改用官方 Git 仓库，并验证真实文件和模板加载。

```powershell
$templatesDir = Join-Path $toolkitRoot 'nuclei-templates'
if (-not (Test-Path -LiteralPath $templatesDir)) {
    git clone --depth 1 https://github.com/projectdiscovery/nuclei-templates.git $templatesDir
    if ($LASTEXITCODE -ne 0) { throw '模板克隆失败' }
}
git -C $templatesDir rev-parse HEAD
$nucleiExe = Join-Path $toolkitRoot 'nuclei\nuclei.exe'
$sampleTemplate = Join-Path $templatesDir 'http\technologies\4D-detect.yaml'
if (-not (Test-Path $sampleTemplate)) { throw '样例模板不存在，选择仓库中真实存在的普通检测模板' }
& $nucleiExe -validate -t $sampleTemplate -disable-update-check
if ($LASTEXITCODE -ne 0) { throw '模板语法验证失败' }
```

上面克隆的是执行时的仓库版本；本次实际提交为 `33a92741d02efb750786956425cb0071943b612c`。若严格复现，可在确认没有本地修改后 fetch 并 checkout 此提交；如果采用更新模板，则应记录新提交，并重新验证与 Nuclei 3.11.1 的兼容性。

只验证一个模板，不能宣称整库全部模板都验证通过，也没有发起实际扫描。

## 17. 先验证二进制，再写工作台配置

先用对应绝对路径检查：

| 程序 | 检查参数/方式 |
|---|---|
| Nmap | `--version`，确认版本及 Npcap |
| Nuclei、HTTPX、DNSX、Subfinder | `-version` |
| ffuf | `-V` |
| fscan | `--help`，**不要用 `-h`，它是目标参数** |
| gogo | `-h` |
| suo5 | `--help` |
| Chisel、frpc、frps | `--version` |
| ksubdomain | `--help`；可另做 `-list-network` |
| Masscan | `--selftest` |
| Impacket | 上节模块导入和 `pip check` |

有些帮助命令会返回非零码，应结合输出判断；不能把真正的缺 DLL、错误架构、拦截或崩溃当成帮助成功。杀毒软件拦截时核对来源并报告，不自动关闭安全软件。

### 17.1 写入绝对路径

将下面代码保存为 `$setupWork/configure_toolkit.mjs`。只在上述检查通过后运行。通过插件自身的保存函数合并配置，保留原有账号字段和其他设置。

```javascript
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(process.argv[2]);
const nmap = path.resolve(process.argv[3]);
process.env.DSH_HOME = root;
const modulePath = path.join(root, 'plugins/dsh-purge/lib/redteam/platform-config.js');
const { savePlatformConfig, platformSummary } = await import(pathToFileURL(modulePath).href);
const rt = path.join(root, 'redteam');
const tk = path.join(rt, 'toolkit');
const paths = {
  nmap,
  nuclei: path.join(tk, 'nuclei/nuclei.exe'),
  masscan: path.join(tk, 'masscan/masscan.exe'),
  fscan: path.join(tk, 'fscan/fscan.exe'),
  gogo: path.join(tk, 'gogo/gogo.exe'),
  suo5: path.join(tk, 'suo5/suo5.exe'),
  frpc: path.join(tk, 'frp/frp_0.71.1_windows_amd64/frpc.exe'),
  frps: path.join(tk, 'frp/frp_0.71.1_windows_amd64/frps.exe'),
  chisel: path.join(tk, 'chisel/chisel.exe'),
  ffuf: path.join(tk, 'ffuf/ffuf.exe'),
  httpx: path.join(tk, 'httpx/httpx.exe'),
  dnsx: path.join(tk, 'dnsx/dnsx.exe'),
  subfinder: path.join(tk, 'subfinder/subfinder.exe'),
  ksubdomain: path.join(tk, 'ksubdomain/ksubdomain.exe'),
  impacket: path.join(tk, 'impacket-venv/Scripts'),
};
const missing = Object.entries(paths).filter(([,p])=>!fs.existsSync(p));
if (missing.length) throw Error('缺少真实路径：' + JSON.stringify(missing));
const templates = path.join(tk, 'nuclei-templates');
if (!fs.existsSync(templates)) throw Error('缺少模板目录');
const config = path.join(rt, 'config.json');
if (fs.existsSync(config)) fs.copyFileSync(config, config + '.backup-' + Date.now());
savePlatformConfig({
  platform: 'windows', toolkitDir: tk, nucleiTemplatesDir: templates,
  tools: paths,
  binDirs: [...new Set(Object.entries(paths).map(([k,p]) => k === 'impacket' ? p : path.dirname(p)))],
  envAdaptConfigured: true, envAdaptSkip: false,
}, rt);
const s = platformSummary(rt);
console.log(JSON.stringify({
  ready: s.adapt.ready, found: s.tools.found, total: s.tools.total,
  missing: s.tools.missing, skipped: s.adapt.skipped,
  tools: s.tools.items,
}, null, 2));
```

```powershell
node (Join-Path $setupWork 'configure_toolkit.mjs') $dshRoot $nmapPath
if ($LASTEXITCODE -ne 0) { throw '环境配置未完成' }
```

frp 解压后有嵌套目录，必须使用真实路径。若使用不同版本或解压结构，先修改 `paths`，不要通过创建空文件骗过检查。

### 17.2 为什么要显式指定 HTTPX

原电脑 PATH 中已经有 `Anaconda\Scripts\httpx.exe`。它是 Python HTTP 客户端，不是 ProjectDiscovery 的同名扫描工具。插件曾把它误计为“已找到”。正确配置应指向 `toolkit\httpx\httpx.exe`，且 `-version` 输出应能确认 ProjectDiscovery HTTPX。

### 17.3 为什么 ready=true 还不是全部完成

此版本 `envAdaptStatus()` 在保存了工具路径后就可能返回 ready。因此必须同时检查 `found=15`、`missing=0`，再加上真实执行检查。

不要设置 `envAdaptSkip=true` 来冒充安装完成；不要创建 `.setup-complete` 来隐藏没有配置的服务。

## 18. 最终验收和一次普通对话

- [ ] 官方 GUI 版本确认是 0.2.1-rc.2，非社区桌面版。
- [ ] 正确的 desktop profile 中注册 dsh-purge 1.1.71。
- [ ] 已保存 package.json、被修改插件文件和旧环境配置的备份。
- [ ] `{{cwd}}` 两处输出已修复，旧字符串识别仍保留。
- [ ] 插件 JavaScript 语法检查通过。
- [ ] Harness 完全退出再打开，普通消息不再报模板变量错误。
- [ ] 插件自身应用结果已查看，未把“安装成功”等同于“宿主补丁完整”。
- [ ] 15 项工具逐个检查通过，HTTPX 没有误认 Python 包。
- [ ] Nmap 7.992 正常加载 Npcap 1.89，驱动运行，安装器结束。
- [ ] Masscan 内置自测通过。
- [ ] Impacket 导入和 pip check 通过。
- [ ] 模板目录存在，记录提交号，样例模板加载验证通过。
- [ ] 工作台环境适配刷新后显示 15/15，未使用跳过标志。
- [ ] 剩余外部资源、额外工具及平台差异明确列出。

界面仍显示旧状态时，先关闭并重新打开环境适配页、刷新；仍不更新则正常退出托盘中的 Harness 后重开。不要直接强制清空缓存或删除 profile。

可把以下消息发给 Harness 做只读预检：

```text
请打开并绑定一个名为“本机环境验证”的演练项目，调用 redteam_preflight。
本轮只检查环境，不执行目标扫描或远程操作。当前是 Windows，请使用环境适配中配置的工具绝对路径。
分别报告：工具可执行性、模板状态、缺少的账号配置、技能中不适用于 Windows 的路径和额外依赖。
不要因为 ready=true 就宣称所有技能可用。
```

## 19. 本次没有配置的部分

| 项目 | 状态和影响 |
|---|---|
| FOFA_KEY | 未提供；相应资产测绘接口未验证 |
| VPS 地址、登录方式、私钥 | 未提供；远程服务和隧道功能未部署或测试 |
| naabu、dirsearch、OneForAll | 本次未安装的附加工具 |
| Behinder、Godzilla、AntSword | 本次未安装的额外软件，不属于 15 项工具完成证明 |
| Linux 专用路径/命令 | 部分技能文档仍引用，需要按平台逐项判断 |
| 所有技能端到端验证 | 未进行；23 个技能正文可加载不代表执行链可用 |

密钥应在本机相应配置界面保存，不能写到安装报告、Git 仓库或公开 Markdown 中。本文不要求购买 VPS 或建立任何远程服务；这些需要后续明确需求。

## 20. 回滚与以后更新

### 20.1 回滚 cwd 修复

完全退出 Harness 后，找到本次生成的 `identity.js.backup-*` 和 `cordis.patch.yml.backup-*`，核对备份内容和时间，恢复到各自原路径。源目录和加载副本可能是硬链接，恢复后分别读取验证，避免混用不同时间的备份。

恢复旧 suffix 可能使 `{{cwd}}` 错误重新出现，因此仅在撤销此次修复或切换兼容版本时使用。

### 20.2 回滚插件注册

若安装后没有其他配置变更，可恢复安装前的 profile `package.json` 备份，再在同一 profile 中执行 `pnpm install`。若后来已有其他改动，应只删除本次新增的 `dsh-purge` dependency 和 bundle 项，保留其余内容。

不要删除整个 `.dsh`、`sessions`、`storages` 或凭据文件。卸载插件不等于自动恢复已应用的宿主补丁；宿主补丁需按插件实际提供的恢复功能或官方重装流程处理，并另行验证。

### 20.3 回滚工具环境

已有 `redteam/config.json` 时恢复相应备份；首次创建时可将新配置改名保留后再验证。工具文件暂时保留也不会自动运行，没必要为了回滚而递归删除整个目录。

### 20.4 以后升级

升级前记录宿主、插件、工具版本与配置备份。插件更新或 pnpm 重装可能覆盖 `node_modules` 中的本地修复，因此应重新检查报错是否仍存在以及源码是否仍符合补丁假设。

不要自动切换到 master/latest 并沿用旧兼容性结论。若上游已正式修复，应优先使用兼容版本的上游修复，而不是继续叠加本地替换。

## 21. 参考来源

- [dsh-purge 仓库](https://github.com/YuJunZhiXue/dsh-purge)
- [本次插件提交](https://github.com/YuJunZhiXue/dsh-purge/tree/8df4406a7c5bddc01091ed20608417390cb457ee)
- [DeepSeek Harness 官方中文 README](https://github.com/deepseek-ai/deepseek-harness/blob/master/README.zh.md)
- [Harness 0.2.1-rc.2 发布记录](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.2.1-rc.2)
- [Nmap 下载](https://nmap.org/download.html)、[Npcap](https://npcap.com/)
- [Nuclei](https://github.com/projectdiscovery/nuclei)、[Nuclei Templates](https://github.com/projectdiscovery/nuclei-templates)
- [Masscan](https://github.com/robertdavidgraham/masscan)、[ksubdomain](https://github.com/knownsec/ksubdomain)、[Impacket](https://github.com/fortra/impacket)

文档内下载地址和校验值基于本次本机安装记录。未来链接失效、版本变化或仓库关闭时，应如实报告，不猜测替代下载地址，也不把尚未验证的步骤写成成功。
