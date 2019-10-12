##### 服务器监控工具

能够对服务器cpu，mem及关键进程生死做出校验并发送告警。

配置文件使用[yaml语法](http://www.ruanyifeng.com/blog/2016/07/yaml.html)
监控时间刻度通过[crontab表达式](https://www.cnblogs.com/javahr/p/8318728.html)设置。

工具依赖：
python：3.x
psutil: 5.6.3
PyYAML: 5.1.2
crontab: 0.22.6


目前还不支持监控远端服务器，计划用fabric实现

欢迎提交issue及commit。