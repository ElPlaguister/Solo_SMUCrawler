import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup as bs
import re
import smtplib
from email.mime.text import MIMEText
import time
from privateManager import getKey
from email.utils import formataddr

def print_time():
    now = time.localtime()
    print ("%04d/%02d/%02d %02d:%02d:%02d" % (now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec))

def no_space(text):
  text1 = re.sub('\nbsp;|&nbsp;|\n|\t|\r|  ', '', text)
  text2 = re.sub('\n\n', '', text1)
  return text2

def setup_session():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    return session

def check_id(ids, type):
    res = []
    f = open(f'private/data_{type}.txt', 'r')
    datum = f.readline().split(' ')
    for id in ids:
        if id not in datum:
            datum.append(id)
            res.append(id)
    datum = ' '.join(datum)
    f.close()
    f = open(f'private/data_{type}.txt', 'w')
    f.write(datum)
    f.close()
    return res

def crawl_swai(session):
    ids = []
    res = []
    for i in range(2):
        endpoint = 'https://swai.smu.ac.kr/bbs/board.php?bo_table=07_01&page=' + str(i + 1)
        try:
            soup = bs(session.get(endpoint).text, 'html.parser')
        except:
            print('crawl swai failed')
            return []

        tableText = soup.find('div', {'class' : 'tbl_head01 tbl_wrap'}).find('tbody')
        urls = [a['href'] for a in tableText.findAll('a')]
        id = [x for x in (url.split('=')[-2].split('&')[0] for url in urls)]
        title = [no_space(t.text) for t in tableText.findAll('a')]
        date = [t.text for t in tableText.findAll('td', {'class' : 'td_datetime'})]

        ids.extend(id)
        for i in range(len(id)):
            res.append({
                'region' : '대학',
                'category' : '[SWAI]',
                'url' : urls[i],
                'title' : title[i],
                'date' : date[i],
                'id' : id[i]
            })
    ids = check_id(ids, 'swai')
    delList = []
    for (i, article) in enumerate(res):
        if article['id'] not in ids:
            delList.append(i)
    for i in delList:
        res[i] = None
    return res

def crawl_smu(session, ignore_cheon = True):
    endpoint = 'https://www.smu.ac.kr/lounge/notice/notice.do'
    try:
        soup = bs(session.get(endpoint).text, 'html.parser')
    except:
        print('crawl smu failed')
        return []
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
            'region' : '대학',
            'category' : category,
            'url' : tmp_url,
            'title' : title,
            'date' : date,
            'id' : id
        }
        articles.append(article)
        ids.append(id)
    ids = check_id(ids, 'smu')
    delList = []
    for (i, article) in enumerate(articles):
        if article['id'] not in ids:
            delList.append(i)
        elif ignore_cheon & (article['region'] == '천안'):
            delList.append(i)
    for i in delList:
        articles[i] = None
    return articles

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

def send_mail(target, content, subject = '오늘의 사업단 글입니다.', fromSite = 'daum'):
    
    msg = MIMEText(content, 'html')
    msg['Subject'] = subject
    msg['To'] = target
    
    try:
        if fromSite == 'google':
            email = getKey('google_email')
            password = getKey('google_password')

            mail_session = smtplib.SMTP('smtp.gmail.com', 587)
            mail_session.starttls()
            mail_session.login(email, password)
            msg['From'] = formataddr(('행정관 아코', 'kritiasmailsender@gmail.com'))
            mail_session.send_message(msg)
        elif fromSite == 'daum':

            email = getKey('daum_email')
            password = getKey('daum_password')

            mail_session = smtplib.SMTP_SSL('smtp.daum.net', 465)
            mail_session.login(email, password)

            msg['From'] = formataddr(('행정관 아코', 'amau_ako@kivotos.tk'))
            mail_session.sendmail(msg['From'], msg['To'], msg.as_string())
    except:
        pass

def start(argv):
    with open('private/target.txt', 'r') as f:
        targets = f.readline().split(' ')
    session = setup_session()
    set_all_read = False
    if len(argv) == 2:
        set_all_read = argv[1] == '1'
    while True:
        print_time()
        contents = [*crawl_swai(session), *crawl_smu(session)]
        if set_all_read:
            break
        mail_body = config_mail(contents)
        if mail_body != None:
            for target in targets:
                send_mail(target, mail_body, subject = '오늘의 학교 정보입니다.')
                print(f'[{target}]님께 메일을 보냈습니다!')
        time.sleep(300)

if __name__ == '__main__':
    start([])