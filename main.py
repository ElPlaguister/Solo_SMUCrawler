import requests
from bs4 import BeautifulSoup as bs
import re
import smtplib
from email.mime.text import MIMEText
import time
from private import privateManager

def crawl_swai():
    urls = []
    for i in range(5):
        endpoint = 'https://swai.smu.ac.kr/bbs/board.php?bo_table=07_01&page=' + str(i + 1)
        soup = bs(requests.get(endpoint).text, 'html.parser')

        tableText = soup.find('div', {'class' : 'tbl_head01 tbl_wrap'}).find('tbody')
        articles = [a['href'] for a in tableText.findAll('a')]
        urls.extend(articles)

    res = [url.split('=')[-2].split('&')[0] for url in urls]
    return res

def add_ids(ids):
    f = open('private/data.txt', 'r')
    datum = f.readline().split(' ')
    for id in ids:
        if id not in datum:
            datum.append(id)
    datum = ' '.join(datum)
    f.close()
    f = open('private/data.txt', 'w')
    f.write(datum)
    f.close()

def check_ids(ids):
    datum = []
    res = []
    with open('private/data.txt', 'r') as f:
        datum = f.readline().split(' ')
    for id in ids:
        if id not in datum:
            res.append(id)
    return res

def set_all_read():
    ids = crawl_swai()
    add_ids(ids)

def no_space(text):
  text1 = re.sub('\nbsp;|&nbsp;|\n|\t|\r|  ', '', text)
  text2 = re.sub('\n\n', '', text1)
  return text2

def get_content_swai(id):
    endpoint = 'https://swai.smu.ac.kr/bbs/board.php?bo_table=07_01&wr_id=' + str(id)
    soup = bs(requests.get(endpoint).text, 'html.parser')
    article = soup.find('article', {'id' : 'bo_v'})

    title = article.find('span', {'class' : 'bo_v_tit'}).text
    title = no_space(title).strip()
    date = ' '.join(article.find('strong', {'class' : 'if_date'}).text.split(' ')[1:])
    content = article.find('div', {'id' : 'bo_v_con'})
    res = {
        'url' : endpoint,
        'title' : title,
        'date' : date,
        'content' : content
    }
    return res

def config_mail(content):
    html = '<html>' + '<header><h1><a href = ' + str(content['url']) + '>' + str(content['title']) + '<a></h1><heeader>' + '<h4>' + str(content['date']) + '</h4>' + str(content['content']) + '</html>'
    return html

def send_mail(target, content, subject = '오늘의 사업단 글입니다.'):
    email = privateManager.getKey('email')
    password = privateManager.getKey('password')

    session = smtplib.SMTP('smtp.gmail.com', 587)
    session.starttls()
    session.login(email, password)

    msg = MIMEText(content, 'html')
    msg['Subject'] = subject
    session.sendmail("Secretary", target, msg.as_string())


if __name__ == '__main__':
    with open('private/target.txt', 'r') as f:
        targets = f.readline().split(' ')
    while True:
        ids = crawl_swai()
        ids = check_ids(ids)
        add_ids(ids)
        for id in ids:
            content = get_content_swai(ids)
            mail_body = config_mail(content)
            for target in targets:
                send_mail(target, mail_body, subject = '[SWAI사업단] ' + content['title'])
        time.sleep(3)