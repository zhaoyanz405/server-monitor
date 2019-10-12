#! /usr/bin/python

"""
@author: yan.zhao
@contact: yan.zhao@idiaoyan.com
@time: 2019/10/11 17:09
"""
import getopt
import logging
import os
import subprocess
import sys
from datetime import datetime

import psutil
import yaml

from ems import send_instant_mail, STATUS_MAIL_SEND_SUCCEED

file_path = os.path.dirname(__file__)


def get_logger():
    log_path = os.path.join(file_path, 'logs', 'monitor.%s.log' % datetime.now().strftime('%Y-%m-%d'))
    logging.basicConfig(filename=log_path, level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)


logger = get_logger()


class ConfigCheckError(Exception):
    pass


def check_config(config: dict):
    """

    :param config:
    :return:
    """
    try:
        server = config.get('server')
        if not server:
            logging.error('there is not server info')
            raise ConfigCheckError

        host, port = server.get('host'), server.get('port')
        if not server or not host or not port:
            logging.error('there is not server info')
            raise ConfigCheckError

        mail = config['mail']
        if not mail:
            logging.error('there is not mail info')
            raise ConfigCheckError

        mail_from = mail['from']
        mail_to = mail['to']
        if not mail or not mail_from or not mail_to:
            logging.error('there is not mail info')
            raise ConfigCheckError

        account = config.get('account')
        if not account:
            logging.error('there is not account info')
            raise ConfigCheckError

        user, passwd = account['user'], account['pass']
        if not user or not passwd:
            logging.error('there is not account info')
            raise ConfigCheckError

    except KeyError:
        logging.error('config error, pls check [account]')
        raise


def get_mail_server(config: dict):
    """

    :param config:
    :return:
    """
    try:
        server = config['server']
        host, port = server['host'], server['port']

        mail = config['mail']
        mail_from = mail['from']

        account = config['account']
        user = account['user']
        passwd = account['pass']
    except KeyError:
        logging.error('config error, pls check [account]')
        raise

    return {'HOST': host, 'PORT': port, 'MAIL_FROM': mail_from, 'USERNAME': user, 'PASSWORD': passwd}


def check_cpu(config: dict):
    """

    :param config:
    :return:
    """
    limit = config.get('limit')
    percent = psutil.cpu_percent(interval=5)
    if percent >= limit:
        cpu_times = psutil.cpu_times()
        msg = '当前1分钟内cpu使用情况：\n' \
              'cpu_percent：%.2f\n' \
              'cpu_times: %s\n' % (percent, cpu_times)

        return False, msg

    return True, None


def check_mem(config: dict):
    """

    :param config:
    :return:
    """
    limit = config.get('limit')
    memory = psutil.virtual_memory()
    percent = memory.percent
    if percent >= limit:
        msg = '当前1分钟内mem使用情况：\nprecent: %.2f\ntotal：%.2f\navailable: %.2f\nused: %.2f\n' \
              'free: %.2f\nbuffers: %.2f\ncached: %.2f' % (memory.percent,
                                                           memory.total / 1024 / 1024, memory.available / 1024 / 1024,
                                                           memory.used / 1024 / 1024,
                                                           memory.free / 1024 / 1024, memory.buffers / 1024 / 1024,
                                                           memory.cached / 1024 / 1024)
        return False, msg
    return True, None


def get_config():
    yaml_path = os.path.join(file_path, 'config.yaml')
    with open(yaml_path) as f:
        config = yaml.load(f.read(), Loader=yaml.FullLoader)
    return config


def monitoring():
    config = get_config()
    lines = list()

    for key, con in config.get('monitor').items():
        res, msg = eval('check_%s' % key)(con)
        if not res:
            lines.append(msg)

    if lines:
        logging.info('send warning email.')
        send(config, lines)


def send(config, lines):
    """

    :param config:
    :param lines:
    :return:
    """
    mail_server = get_mail_server(config)
    mail = config.get('mail')
    account = config.get('account')
    status = send_instant_mail(mail_server=mail_server, mail_from=account.get('user'), subject=mail.get('subject'),
                               content='\n'.join(lines),
                               mail_to=mail.get('to'), copy_to=mail.get('cc'))
    if status == STATUS_MAIL_SEND_SUCCEED:
        print('[send email] success')
    else:
        print('[send email] fail.')
        print('status:', status)
        print("""
            STATUS_MAIL_SEND_FAILED = -1  # 失败的
            STATUS_MAIL_SEND_SUCCEED = 1  # 成功的
            STATUS_MAIL_SERVER_ERROR = 2  # 邮件服务器配置错误
            STATUS_MAIL_SERVER_HOST_ERROR = 3  # 邮件服务器host为空
            STATUS_MAIL_SERVER_USERNAME_ERROR = 4  # 邮件服务器用户名为空
            STATUS_MAIL_SERVER_PASSWORD_ERROR = 5  # 邮件服务器密码为空
            STATUS_MAIL_SUBJECT_NONE_ERROR = 6  # 邮件主题为空
            STATUS_MAIL_SUBJECT_PARAMS_ERROR = 7  # 邮件主题参数格式错误
            STATUS_MAIL_FROM_ADDRESS_NONE_ERROR = 8  # 邮件发送地址为空
            STATUS_MAIL_FROM_ADDRESS_PARAMS_ERROR = 9  # 邮件发送地址参数格式错误
            STATUS_MAIL_TO_ADDRESS_NONE_ERROR = 10  # 邮件目标地址为空
            STATUS_MAIL_TO_ADDRESS_PARAMS_ERROR = 11  # 邮件目标地址参数格式错误
            STATUS_MAIL_CONTENT_NONE_ERROR = 12  # 邮件内容为空
            STATUS_MAIL_CONTENT_PARAMS_ERROR = 13  # 邮件内容参数错误
            STATUS_MAIL_HELO_ERROR = 14  # 无法连接到邮件服务器
            STATUS_MAIL_REJECTED_ALL_ERROR = 15  # 服务器拒绝所有接收方
            STATUS_MAIL_SENDER_REFUSED_ERROR = 16  # 服务器拒绝发送地址请求
            STATUS_MAIL_UNEXPECTED_CODE_ERROR = 17  # 服务器返回其他错代码""")


def load_monitor():
    clear_monitor()
    print('load monitor start.')
    cmd = r"sed -i '$a\python %s' " % __file__
    try:
        subprocess.run(args=cmd, check=True)
    except subprocess.CalledProcessError:
        print('load monitor to crondtab fail. the cmd is %s. pls retry by manual.' % cmd)
    print('load monitor done.')


def clear_monitor():
    print('clear monitor start.')
    cmd = r"sed -i '/python.*monitor/d' /etc/crondtab"
    try:
        subprocess.run(args=cmd, check=True)
    except subprocess.CalledProcessError:
        print('clear monitor from crondtab fail. the cmd is %s. pls retry by manual.' % cmd)
    print('clear monitor done.')


def usage():
    """

    :return:
    """
    _msg = """
    Usage:
        python monitor.py [options]
        
        -h  --help 
        -t  --test test the config, and send confirm email.
        --start  run monitor
        --stop   stop monitor
        
        For more details see http://code.wenjuan.com/zhaoy/server-monitor.

    """
    print(_msg)


if __name__ == '__main__':
    try:
        options, args = getopt.getopt(sys.argv[1:], "h:p:i:t", ["help", "start", "stop", "test"])
    except getopt.GetoptError:
        usage()
        sys.exit(-1)

    if not options:
        usage()

    for name, value in options:
        if name in ("-h", "--help"):
            usage()
            break
        if name == "--start":
            load_monitor()
            break

        if name == '--stop':
            clear_monitor()
            break

        if name == '--monitor':
            monitoring()
            break

        if name in ("-t", "--test"):
            send(get_config(), ['邮件功能测试正常'])
            break

    sys.exit(0)
