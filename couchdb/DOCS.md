# CouchDB

安装与迁移说明见[仓库 README](https://github.com/autofeet/ha-couchdb#readme)。

在“信息”页打开“显示在侧边栏”，点击左侧 CouchDB 即可打开 Fauxton 管理页面。
此入口使用 HA 登录身份，仅供 HA 管理员；无需再次输入 CouchDB 密码。
LiveSync 客户端继续连接原来的 5984 API，并使用 CouchDB 自身账号密码。

配置 `username`、`password` 后启动。HTTP API 为 `http://HA地址:5984/`，Fauxton 为 `/_utils/`。
移动端使用 HTTPS 反向代理地址。数据库和配置都保存在本组件的持久数据目录，备份时务必包含本组件。

HA 配置中的管理员账号是权威来源；修改并重启会替换原来的服务器管理员。
