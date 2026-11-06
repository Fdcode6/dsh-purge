# Windows 安装包使用说明

本目录是本机整理的 **Windows x64 离线安装材料**，不是上游官方新发行版。用于复现官方 DeepSeek Harness 0.2.1-rc.2 + dsh-purge 1.1.71 的安装和本地兼容修复。

## 在另一台电脑上怎么操作

1. 把整个 `dsh-purge` 文件夹复制过去；也可以只复制完整的 `windows-install` 文件夹。不要只复制启动器。
2. 双击 **`Start-Windows-Setup.cmd`**。
3. 菜单 1 安装 Python 3.13.1 x64；已经有兼容 Python 3.13 x64 时可跳过。离线 wheel 针对 CPython 3.13 / Windows x64，不适用于 3.12、3.14 或 ARM64 原生解释器。
4. 菜单 2 安装官方 Harness。启动一次，完成必要的初始化/登录，让它创建 `desktop` profile，随后从托盘彻底退出。已有兼容宿主可跳过安装。
5. 菜单 3 安装 Nmap 7.992 和附带的 Npcap。按向导完成，不要留下未完成的驱动安装窗口。管理员确认由用户操作。
6. 菜单 4 配置插件和环境。确认实际 `DSH_HOME`；通常按 Enter 使用用户目录下 `.dsh`。脚本会备份现有配置、安装本地源码快照、修复 `{{cwd}}` 和红队预设 `toolFilter` 兼容错误、安装工具和 Python 依赖，并写入本机绝对路径。
7. 菜单 5 检查 15 项工具。重新打开 Harness，在插件中查看“环境适配”，按完整指南完成“清洗 → 应用”、重启及普通对话验证。

启动器的菜单使用英文，具体含义如上。可以把这个文件和 `docs/Windows安装与环境配置指南.md` 一起交给另一台电脑上的 AI 助手。

**不要在这个大文件夹的根目录执行 `dsh plugin add .` 或把整个目录复制进 `.dsh/plugins`。** 安装脚本使用 `sources/dsh-purge-1.1.71-original.tar.gz`，因此不会把数百 MB 的安装材料套娃复制进去。

## 目录用途

```text
windows-install/
  Start-Windows-Setup.cmd       双击入口
  README.md                    本说明
  manifest.json                全部安装材料 SHA-256 清单
  portable-tools.json          便携工具与资产文件的映射
  installers/                  Harness、Python、Nmap 安装器
  runtime/                     Node ZIP 和 pnpm TGZ，无需全局安装 Node/pnpm
  tools/                       固定版本工具包、Masscan 本地构建、ksubdomain、模板快照
  python-wheels/               Impacket 及锁定的依赖 wheel
  sources/                     插件原始源码快照、修改后的 Masscan 源码
  scripts/                     离线配置、cwd 修复和安装菜单
  checksums/                   原下载校验文件
  docs/                        完整指南、文件来源及验证结果
```

原来放在仓库根目录的配套 EXE 已移动到：

```text
windows-install/installers/deepseek-harness-0.2.1-rc.2-win-x64.exe
```

## 离线与联网边界

- 已备齐本次安装需要的 Node、pnpm、Python 安装器、插件源码、15 项工具材料、Impacket wheel 和模板快照。
- 菜单 4 使用 `pnpm --offline`、`pip --no-index`，不会临时去网上补包。已有 profile 中的其他依赖若没有离线缓存，pnpm 仍可能失败；此时保留备份并逐项处理，不能删除原依赖来强行通过。
- Harness 首次启动、账号登录、模型调用、签名吊销状态检查或上游宿主自身初始化可能需要联网。这不是“整台电脑永久离线运行”的承诺。
- 不需要复制旧电脑的 `.credentials.yaml`、会话、FOFA 密钥、私钥或整个 `.dsh`；这些没有放进安装包。
- 不需要在新电脑编译 Masscan：包含本次通过自测的 Windows x64 二进制和对应修改后源码。编译日期为本次构建日期，只有一处 MSVC 版本条件兼容修改。
- 未包含 FOFA/VPS 账号、额外 WebShell 软件、其他附加技能依赖。15/15 工具就绪不等于所有技能端到端可用。

## 现有安装与重复执行

- 配置前必须完全退出 Harness。脚本不强杀应用。
- 使用已经存在的 1.1.71 插件目录；不同版本停止处理，避免覆盖用户升级或修改。
- 已存在的工具目录保留，不盲目覆盖；执行检查失败时明确报告，需要助手核对实际内容后处理。
- 配置脚本备份 profile 的 package.json、pnpm 锁文件、工作台 config.json 和被修改的插件文件。
- cwd 修复可重复执行，兼容 pnpm 使用硬链接的情况。
- 不写全局 PATH，不自动开启网络服务，不执行目标扫描，不设置 `envAdaptSkip=true`，不伪造 `.setup-complete`。
- 外部工具软件各自许可仍然适用；本包用于用户自己的机器迁移，不代表获得公开再分发或商业使用授权。原压缩包和源码中的许可文件保留。

## 自定义 Nmap 路径

如果 Nmap 不在 Program Files 默认目录，可让助手用 Python 3.13 x64 执行：

```powershell
py -3.13 .\scripts\offline_setup.py configure --dsh-root 'D:\实际的dsh-home' --nmap 'D:\Tools\Nmap\nmap.exe'
```

路径仅为示例，不要照抄。配置成功后本机验证结果保存到 `DSH_HOME/redteam/local-install-checks.json`；Node/pnpm 解压缓存保存到 `%LOCALAPPDATA%/DshPurgeSetup/1.1.71`。

## 完成标准

先查看 `docs/打包验证结果.md` 了解本包已测试和未测试的范围。新电脑必须再次确认：驱动正常、全部工具检查通过、环境配置 15/15、Harness 重启后普通对话成功、宿主补丁状态明确。安装脚本完成不自动代替这些界面验证。

## 仓库管理

本分支包含完整离线安装材料，无需 Git LFS：

```powershell
git clone --branch windows-offline-setup https://github.com/Fdcode6/dsh-purge.git
```

约 289 MB 的 Harness 安装器以五个 `.part001` 至 `.part005` 分卷保存。双击 `Start-Windows-Setup.cmd` 后，入口自动校验分卷、合并成 EXE，再校验完整 SHA-256。分卷不能单独运行，也不能漏下载。已有完整且校验通过的 EXE 时跳过合并。

直接使用 Python 配置脚本前，请先运行 `scripts/Restore-Installer.ps1`，或先启动一次双击入口。合并需要额外约 289 MB 磁盘空间。GitHub Download ZIP 应选择本分支；完整解压后再启动。

系统要求：Windows 10/11 x64，推荐 Windows 11；不支持 Windows 7/8/8.1 或 32 位 Windows。本分支保留上游许可，不改变各组件的授权条件。

## 红队模式加载失败修复

若出现 `toolFilter is no longer supported`，请看 [红队预设加载修复](docs/红队预设加载修复.md)。新安装的菜单 4 已包含修复；已有安装可单独运行修复脚本，无需重装工具环境。本机已重启确认 `ok=true`、`broken=null`，完整演练任务尚未验证。

## 2026-11-06：禁止在线覆盖本地修复

本离线包已关闭插件的内置更新机制，安装菜单 4 自动应用更新锁。检测更新不联网，在线升级、切换版本及回退均被拒绝。已有安装需完全退出并重开 Harness。此锁不控制官方宿主自身升级。操作、验证和维护边界见 [插件更新锁定说明](docs/插件更新锁定说明.md)。

## 官方宿主更新关闭（2026-11-06）

菜单 2 安装后自动关闭官方更新源；安装结束时不要启动 Harness。已安装或误启动的情况，完全退出后选菜单 6。官方 EXE 原样保留，单独运行它不会自动关闭更新。详见 [官方桌面端更新关闭说明](docs/官方桌面端更新关闭说明.md)。
