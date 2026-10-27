# CouchDB

安装与迁移说明见[仓库 README](https://github.com/autofeet/ha-couchdb#readme)。

配置 `username`、`password` 后启动。HTTP API 为 `http://HA地址:5984/`，Fauxton 为 `/_utils/`。
移动端使用 HTTPS 反向代理地址。数据库和配置都保存在本组件的持久数据目录，备份时务必包含本组件。

HA 配置中的管理员账号是权威来源；修改并重启会替换原来的服务器管理员。
