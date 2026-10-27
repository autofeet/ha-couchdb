# CouchDB for Home Assistant OS

基于 **Docker Official Image `couchdb`** 的轻量 HA 附加组件封装，用于 Obsidian Self-hosted LiveSync。
当前 CouchDB：**3.5.3**。支持 **amd64 / aarch64**。由 HA 在设备上构建，无需第三方 CouchDB 镜像或 GHCR 账号。

这不是 Apache 或 Home Assistant 官方附加组件；服务本体使用官方镜像，本仓库只负责 HA 适配。

## 安装

1. HA → 设置 → 应用 / 附加组件 → 商店 → 右上角菜单 → 仓库。
2. 添加 `https://github.com/autofeet/ha-couchdb`。
3. 安装 **CouchDB**，首次安装需要下载基础镜像并构建，可能需要几分钟。
4. 在配置页设置 `username` 和 `password`。密码不能为空，不能包含控制字符或首尾空白；不能以分号开头或包含“空白后紧跟分号”，以免被 CouchDB 当作配置注释。
5. 启动，启用“开机启动”和看门狗。API 地址为 `http://HA地址:5984/`，管理界面为 `http://HA地址:5984/_utils/`。
6. 在 LiveSync 中配置服务器地址、账号、密码和数据库名称，运行其连接与配置检查。

在应用“信息”页打开“显示在侧边栏”，左侧 **CouchDB** 会在 HA 内打开 Fauxton 管理页面。
管理入口经过 HA 登录校验，无需再次登录 CouchDB；仅接受 Supervisor 内部连接，不额外开放管理端口。

移动端使用 HTTPS 地址；在已有反向代理上将专用域名转发到 HA 的 5984 端口。
HA 自身的 HTTPS 地址或远程访问服务不会自动代理 CouchDB。不要把未加密的 5984 直接暴露到公网。

## 存储与配置

- 数据库与索引：附加组件私有目录 `/data/couchdb`。
- CouchDB 运行配置：`/data/local.d/docker.ini`，随重启、容器重建和更新保留。
- HA 备份中**包含本附加组件及其数据**时，才能备份这些内容；不要只备份 HA Core。
- HA 选项控制本实例唯一的服务器管理员。修改选项并重启会替换原管理员；不要在 Fauxton 中另加需要长期保留的服务器管理员。普通数据库用户不受此限制。
- 认证、单节点模式、数据目录、端口、LiveSync CORS 和请求大小是封装管理的配置，启动时重新应用。其他 CouchDB 运行配置保留。
- 不请求 Docker socket、主机网络、宿主机权限或 Home Assistant 管理 API。

## 更新

仓库每天北京时间 **10:23** 检查 Docker Hub 官方 CouchDB 稳定标签，也可在 Actions 手动运行。
只跟踪当前主版本，同时要求 amd64 和 arm64 镜像。新版通过单元测试及两种架构的容器测试后，提交 PR 并自动合并；合并时锁定本次验证的提交。测试失败不会发布更新。
PR 合并后，HA 刷新商店便能检测到新的附加组件版本；是否自动安装由 HA 中的“自动更新”开关决定。

维护者需在仓库 Settings → Actions → General → Workflow permissions 勾选
**Allow GitHub Actions to create and approve pull requests**，否则检查仍能运行，但不能提交更新 PR。
工作流按需申请 `contents: write` 和 `pull-requests: write`，无需 PAT。
GitHub 可能在公共仓库长期没有活动后暂停定时任务，届时需要在 Actions 中重新启用。

## 从现有 CouchDB 迁移

先对所有 Obsidian 笔记库和旧 CouchDB 做独立备份。先安装本组件，保持旧服务可用。
暂停各设备同步，通过 CouchDB 自带的复制功能将目标数据库复制到新实例，验证数据、权限和加密设置后，逐台切换客户端。
复制数据库不会自动复制服务器管理员、普通用户数据库或目标数据库的 `_security` 权限；按原配置核对这些项目。
所有设备完成双向测试后再停旧服务。不要把未经确认的本地库直接用于“重建/覆盖远端”。

## 验证

`python3 -m unittest discover -s tests -v` 检查选项处理、配置保留、凭据轮换和上游版本筛选。
GitHub CI 在原生 amd64 / aarch64 上构建并检查认证、CORS、系统数据库、容器替换后的数据保留和凭据轮换。
测试通过不代表已经在你的 HA 设备安装或完成真实 LiveSync 数据迁移。

上游：[Apache CouchDB 镜像](https://hub.docker.com/_/couchdb) · [Self-hosted LiveSync](https://github.com/vrtmrz/obsidian-livesync)

图标使用 [Apache Fauxton 的 CouchDB 原始图标](https://github.com/apache/couchdb-fauxton/blob/main/assets/img/couchdb-logo.png)。Apache CouchDB 与其标识属于 Apache Software Foundation；本封装不是官方发行的 HA 应用。
