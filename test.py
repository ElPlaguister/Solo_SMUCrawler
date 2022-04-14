import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup as bs
import re
import smtplib
from email.mime.text import MIMEText
import time
from private import privateManager

def setup_session():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)

    return session

def crawl_swai(session):
    urls = []
    for i in range(5):
        endpoint = 'https://swai.smu.ac.kr/bbs/board.php?bo_table=07_01&page=' + str(i + 1)
        soup = bs(session.get(endpoint).text, 'html.parser')

        tableText = soup.find('div', {'class' : 'tbl_head01 tbl_wrap'}).find('tbody')
        articles = [a['href'] for a in tableText.findAll('a')]
        urls.extend(articles)

    res = [url.split('=')[-2].split('&')[0] for url in urls]
    return res

def crawl_smu(session):
    endpoint = 'https://www.smu.ac.kr/lounge/notice/notice.do'
    soup = bs(session.get(endpoint).text, 'html.parser')
    tableText = soup.find('ul', {'class' : 'board-thumb-wrap'})
    ids = [no_space(a.text.strip()).replace('No.', '') for a in tableText.findAll('li', {'class' : 'board-thumb-content-number'})]
    return ids

def add_swai_ids(ids):
    f = open('private/data_swai.txt', 'r')
    datum = f.readline().split(' ')
    for id in ids:
        if id not in datum:
            datum.append(id)
    datum = ' '.join(datum)
    f.close()
    f = open('private/data_swai.txt', 'w')
    f.write(datum)
    f.close()

def check_swai_ids(ids):
    datum = []
    res = []
    with open('private/data_swai.txt', 'r') as f:
        datum = f.readline().split(' ')
    for id in ids:
        if id not in datum:
            res.append(id)
    return res

def add_smu_id(ids):
    f = open('private/data_smu.txt', 'r')
    datum = f.readline().split(' ')
    for id in ids:
        if id not in datum:
            datum.append(id)
    datum = ' '.join(datum)
    f.close()
    f = open('private/data_smu.txt', 'w')
    f.write(datum)
    f.close()

def check_smu_id(ids):
    res = []
    with open('private/data_smu.txt', 'r') as f:
        datum = f.readline().split(' ')
    for id in ids:
        if id not in datum:
            res.append(id)
    return res

def set_all_read():
    ids = crawl_swai()
    add_swai_ids(ids)

def no_space(text):
  text1 = re.sub('\nbsp;|&nbsp;|\n|\t|\r|  ', '', text)
  text2 = re.sub('\n\n', '', text1)
  return text2

def crawl_smu(session, set_all_read = False, ignore_cheon = True):
    endpoint = 'https://www.smu.ac.kr/lounge/notice/notice.do'
    soup = bs(session.get(endpoint).text, 'html.parser')
    tableText = soup.find('ul', {'class' : 'board-thumb-wrap'})
    contents = tableText.findAll('dl', {'class' : 'board-thumb-content-wrap'})
    articles = []
    ids = []
    for content in contents:
        tmp = content.find('dd', {'class' : 'board-thumb-content-info'})
        id = no_space(tmp.find('li', {'class' : 'board-thumb-content-number'}).text.strip()).replace('No.', '')
        date = re.findall(r'[0-9]+-[0-9]+-[0-9]+', tmp.find('li', {'class', 'board-thumb-content-date'}).text)[0]
        region = content.find('span', {'class' : 'cmp'}).text
        category = content.find('span', {'class' : 'cate'}).text
        tmp_url = 'https://www.smu.ac.kr/lounge/notice/notice.do?mode=view&articleNo=' + id + '&article.offset=0&articleLimit=10'
        title = no_space([a.text for a in content.find('dt', {'class' : 'board-thumb-content-title'}).findAll('a')][-1])
        article = {
            'region' : region,
            'category' : category,
            'url' : tmp_url,
            'title' : title,
            'date' : date,
            'id' : id
        }
        articles.append(article)
        ids.append(id)
    ids = check_smu_id(ids)
    if set_all_read:
        add_smu_id(ids)
        return
    delList = []
    for (i, article) in enumerate(articles):
        if article['id'] not in ids:
            delList.append(i)
        elif ignore_cheon & (article['region'] == '천안'):
            delList.append(i)
    for i in delList:
        articles[i] = None
    return articles

def get_content_swai(id, session):
    endpoint = 'https://swai.smu.ac.kr/bbs/board.php?bo_table=07_01&wr_id=' + str(id)
    soup = bs(session.get(endpoint).text, 'html.parser')
    article = soup.find('article', {'id' : 'bo_v'})

    title = article.find('span', {'class' : 'bo_v_tit'}).text
    title = no_space(title).strip()
    date = article.find('strong', {'class' : 'if_date'}).text.split(' ')[1]
    content = article.find('div', {'id' : 'bo_v_con'})
    res = {
        'region' : '서울',
        'category' : '[SWAI]',
        'url' : endpoint,
        'title' : title,
        'date' : date,
        'content' : content
    }
    return res

def config_mail(contents):
    with open('mailFrame.html', 'r') as f:
        frame = ' '.join(f.readlines())
    none_count = 0
    for i in range(len(contents)):
        if contents[i] == None:
            none_count += 1
            continue
        with open('content.html', 'r') as f:
            c = ' '.join(f.readlines())
        c = c.replace('__region__', contents[i]['region'])
        c = c.replace('__url__', contents[i]['url'])
        c = c.replace('__title__', contents[i]['title'])
        c = c.replace('__date__', contents[i]['date'])
        c = c.replace('__category__', contents[i]['category'])
        c += '__content__'
        frame = frame.replace('__content__', c)
    frame = frame.replace('__content__', '')
    if none_count == len(contents):
        frame = None
    return frame

def send_mail(target, content, subject = '오늘의 사업단 글입니다.'):
    email = privateManager.getKey('email')
    password = privateManager.getKey('password')

    mail_session = smtplib.SMTP('smtp.gmail.com', 587)
    mail_session.starttls()
    mail_session.login(email, password)

    msg = MIMEText(content, 'html')
    msg['Subject'] = subject
    mail_session.sendmail("Secretary@gmail.com", target, msg.as_string())

if __name__ == '__main__':
    with open('private/target.txt', 'r') as f:
        targets = f.readline().split(' ')
    session = setup_session()
    ids = [713, 708, 706, 351]
    contents = []
    for id in ids:
        contents.append(get_content_swai(id, session))
    contents.extend(crawl_smu(session))
    mail_body = config_mail(contents)

    if mail_body != None:
        send_mail(targets[0], mail_body, subject = '오늘의 학교 정보입니다.')