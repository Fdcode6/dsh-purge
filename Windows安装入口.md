# 本地 Windows 安装材料入口

配套官方 EXE 已整理到 `windows-install/installers/deepseek-harness-0.2.1-rc.2-win-x64.exe`。

复制本文件夹到另一台 Windows x64 电脑后，阅读 [离线安装说明](windows-install/README.md)，双击 `windows-install/Start-Windows-Setup.cmd`。

完整安装、修复与回滚文档：[Windows安装与环境配置指南](windows-install/docs/Windows安装与环境配置指南.md)。

这套目录包含插件源码快照、工具包、Node/pnpm、Python 安装器、Impacket 离线依赖和模板快照；请直接复制文件夹，本分支包含完整离线材料，超大 EXE 以分卷存放，双击入口自动合并校验；无需 Git LFS。

不要对这个带离线材料的大仓库直接执行 `dsh plugin add .`；安装向导只使用内部独立源码快照，避免递归复制安装包。

红队模式显示“加载失败”时，请阅读 [红队预设加载修复](windows-install/docs/红队预设加载修复.md)。本分支已包含修复，离线安装菜单 4 自动应用。
